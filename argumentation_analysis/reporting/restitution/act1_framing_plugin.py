"""Acte I generator — mise en situation (framing), before the microscope.

Epic #1134 (Restitution) / Track R2 #1136. LLM-conducted, woven per spec §4.
Consumed by the R6 renderer to populate ``RestitutionActs.act1_framing``.

Design (spec §1.1 + §4 + §7, issue #1136, dispatch coord R428):
  - Everything that makes Acte II legible, produced BEFORE citing the text:
    1. **Le texte** — discourse genre, speaker role, channel, context (opaque
       metadata).
    2. **Les enjeux** — what is at stake, for whom, what asymmetry.
    3. **Le spectre attendu** — the fallacies an informed listener should watch
       for given this *genre* of discourse. **Anticipation, not detection** —
       DERIVED by walking the taxonomy: families whose ``common_contexts`` match
       the discourse genre. Never hardcoded (DoD).
    4. **La lecture game-theoretic** — players, interests, expected moves,
       asymmetric info (from stakeholders + the argument inventory structure).
  - Acte I is the ONLY act that may anticipate (spec §1.1). Every framework
    citation still gets a narrative anchor (passes the §4 gate — this module
    self-checks with ``ReadabilityGate``).
  - **LLM-conducted**: the framing VARIES by corpus (no template #1108/#405).
    Fail-loud when no LLM is injected — empty string + explicit status; the
    renderer reports the gap honestly (anti-pendule #1019/#369). Missing
    metadata is named ("contexte non renseigné"), never invented.

Privacy HARD: opaque IDs only (``Speaker_A``, ``era_A``, ``State_Q``). The
prompt carries the OPAQUE_ID_DIRECTIVE (FB-34). Corpus-derived fields
(stakes/stakeholders text) are truncated before entering the prompt. The
taxonomy families are constants (safe to surface).

Testability: ``build_act1_evidence`` is deterministic (no LLM/JVM/API); the LLM
is an injectable async callable ``Callable[[str], Awaitable[str]]`` (FB-29/38),
so unit tests pass a stub and need no kernel.

Mirrors the R3 act-plugin pattern (``act2_narrative_plugin``) — R4 will mirror
this in turn (same 3 infra files, append-only).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

import yaml

from .readability_gate import GateVerdict, ReadabilityGate
from .virtuous_identification import VirtuousModeAssessment, detect_virtuous_mode

logger = logging.getLogger(__name__)

# An async LLM callable: prompt in, completion text out (FB-29/38 injectable).
LlmCallable = Callable[[str], Awaitable[str]]

# Truncation caps for corpus-derived fields entering the prompt.
_STAKE_CAP = 200
_STAKEHOLDER_CAP = 120
_META_CAP = 160

# Single source of truth: the taxonomy families YAML (same data the
# TaxonomyExplorerPlugin loads). We read it directly to stay file-disjoint from
# the SK plugin_framework (heavy JVM deps) and keep the restitution package
# dependency-free. If the file moves, the loader fails-loud (no spectrum).
_FALLACY_FAMILIES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "plugin_framework",
    "core",
    "plugins",
    "standard",
    "taxonomy_explorer",
    "data",
    "fallacy_families.yaml",
)

# Reserved genre sentinel when no genre signal is present → the spectrum is the
# full taxonomy (general watch-list), reported honestly.
_GENRE_UNKNOWN = "__unknown__"


# --- evidence dataclasses ----------------------------------------------------


@dataclass
class ExpectedFamily:
    """One fallacy family an informed listener should watch for (anticipation)."""

    family_id: str
    name_fr: str
    matched_contexts: List[str]  # the common_contexts that matched the genre
    severity_weight: float


@dataclass
class StakeholderInfo:
    """One stakeholder for the game-theoretic read."""

    role: str
    detail: str


@dataclass
class Act1Evidence:
    """Deterministic evidence bundle for the Acte I framing."""

    # Le texte
    metadata: Dict[str, str] = field(default_factory=dict)
    genre: str = ""
    genre_source: str = ""  # transparency: which field supplied the genre
    # Les enjeux
    stakes: List[str] = field(default_factory=list)
    rhetorical_register: str = ""
    discursive_arena: str = ""
    has_stakes: bool = False
    # Spectre attendu (derived from taxonomy common_contexts)
    expected_spectrum: List[ExpectedFamily] = field(default_factory=list)
    spectrum_general: bool = False  # True when genre unknown → full taxonomy
    spectrum_available: bool = True  # False when taxonomy could not load
    # Game-theoretic
    stakeholders: List[StakeholderInfo] = field(default_factory=list)
    arg_count: int = 0
    # DERIVED virtuous flag (spec §5.1) — when the state characterises the text
    # as virtuous, the spectrum framing shifts from "what to watch for" to
    # "what could derail but doesn't" (anticipation that did not materialise).
    virtuous_mode: Optional[VirtuousModeAssessment] = None
    # Epic #1258 / Track 1 #1259 — when True, build_act1_prompt DROPS the
    # opaque-ID directive so the readable restitution names the real speaker/arena.
    deanonymized: bool = True


@dataclass
class Act1Result:
    """Outcome of :func:`build_act1_framing`.

    ``status`` is ``"woven"`` | ``"unavailable"`` | ``"empty_state"``.
    ``gate_verdict`` is the honest §4 self-check.
    """

    narrative: str
    status: str
    gate_verdict: Optional[GateVerdict] = None
    degraded: Dict[str, str] = field(default_factory=dict)
    # True when the framing was conducted with the virtuous anticipation shift
    # (spec §5): the spectrum is read as "what could derail but doesn't".
    is_virtuous: bool = False


# --- taxonomy loader (minimal, file-disjoint) --------------------------------


_families_cache: Optional[List[Dict[str, Any]]] = None


def _load_families() -> List[Dict[str, Any]]:
    """Load the fallacy families from the taxonomy YAML (cached, fail-loud).

    Returns a list of ``{family, name_fr, common_contexts, severity_weight}``
    dicts, or an empty list if the file is unavailable (the caller reports the
    spectrum as unavailable — anti-pendule: never fabricate families).
    """
    global _families_cache
    if _families_cache is not None:
        return _families_cache
    try:
        with open(_FALLACY_FAMILIES_PATH, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or []
    except (OSError, yaml.YAMLError) as exc:
        logger.warning(
            "Acte I: fallacy families taxonomy unavailable (%s) — expected "
            "spectrum will be reported as indisponible (fail-loud).",
            exc,
        )
        _families_cache = []
        return _families_cache
    families: List[Dict[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        fid = entry.get("family")
        if not fid:
            continue
        families.append(
            {
                "family": str(fid),
                "name_fr": str(entry.get("name_fr", fid)),
                "common_contexts": [
                    str(c).lower() for c in (entry.get("common_contexts") or [])
                ],
                "severity_weight": float(entry.get("severity_weight", 0.5)),
            }
        )
    _families_cache = families
    return _families_cache


def reset_taxonomy_cache() -> None:
    """Reset the families cache (test hook)."""
    global _families_cache
    _families_cache = None


# --- deterministic evidence builder (no LLM) ---------------------------------


def _truncate(text: Any, cap: int) -> str:
    if not text:
        return ""
    s = str(text).strip()
    return s if len(s) <= cap else s[:cap].rstrip() + " […]"


def _derive_genre(state: Any) -> Tuple[str, str]:
    """Derive the discourse genre (the concrete discursive domain) from the state.

    The arena is preferred over the register because the taxonomy
    ``common_contexts`` encode *domains* (politique, marketing, scientifique…),
    not Aristotelian registers (délibératif, polémique) — a register alone never
    narrows the expected spectrum. The register is still surfaced separately in
    the framing (``evidence.rhetorical_register`` → stakes_block), so no signal
    is lost. Returns (genre_lowercased, source_label); unknown →
    (``_GENRE_UNKNOWN``, "").
    """
    stakes = getattr(state, "stakes_and_stakeholders", {}) or {}
    if isinstance(stakes, dict):
        arena = str(stakes.get("discursive_arena", "") or "").strip()
        if arena:
            return arena.lower(), "discursive_arena"
        register = str(stakes.get("rhetorical_register", "") or "").strip()
        if register:
            return register.lower(), "rhetorical_register"
    metadata = getattr(state, "source_metadata", {}) or {}
    if isinstance(metadata, dict):
        for key in ("genre", "register", "type", "arena", "context"):
            val = str(metadata.get(key, "") or "").strip()
            if val:
                return val.lower(), f"source_metadata.{key}"
    return _GENRE_UNKNOWN, ""


def _derive_expected_spectrum(
    families: List[Dict[str, Any]], genre: str
) -> Tuple[List[ExpectedFamily], bool]:
    """Derive the expected spectrum by matching genre → ``common_contexts``.

    A family is expected when its ``common_contexts`` contains the genre (or the
    genre contains a context — bidirectional substring, FR). When the genre is
    unknown, returns the FULL taxonomy (general watch-list) with
    ``spectrum_general=True`` (honest: "genre non renseigné — spectre général").
    """
    if not families:
        return [], False
    if genre == _GENRE_UNKNOWN or not genre:
        # General watch-list: all families, sorted by severity (most severe
        # first) so the framing foregrounds the highest-stakes watch.
        ordered = sorted(families, key=lambda f: f["severity_weight"], reverse=True)
        return [
            ExpectedFamily(
                family_id=f["family"],
                name_fr=f["name_fr"],
                matched_contexts=[],
                severity_weight=f["severity_weight"],
            )
            for f in ordered
        ], True
    matches: List[ExpectedFamily] = []
    for f in families:
        contexts = f["common_contexts"]
        hit = [c for c in contexts if c and (c in genre or genre in c)]
        if hit:
            matches.append(
                ExpectedFamily(
                    family_id=f["family"],
                    name_fr=f["name_fr"],
                    matched_contexts=hit,
                    severity_weight=f["severity_weight"],
                )
            )
    # If the genre matched nothing, fall back to the general watch-list
    # (honest: the genre is too specific to narrow the spectrum).
    if not matches:
        ordered = sorted(families, key=lambda f: f["severity_weight"], reverse=True)
        return [
            ExpectedFamily(
                family_id=f["family"],
                name_fr=f["name_fr"],
                matched_contexts=[],
                severity_weight=f["severity_weight"],
            )
            for f in ordered
        ], True
    matches.sort(key=lambda m: m.severity_weight, reverse=True)
    return matches, False


def build_act1_evidence(state: Any) -> Act1Evidence:
    """Build the deterministic Acte I framing evidence from a shared state.

    No LLM, no JVM — pure state + taxonomy extraction. Privacy: corpus-derived
    fields (stakes, stakeholders) are truncated; metadata stays opaque.
    """
    metadata = getattr(state, "source_metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    metadata_view = {
        str(k): _truncate(v, _META_CAP) for k, v in metadata.items() if v
    }

    stakes_obj = getattr(state, "stakes_and_stakeholders", {}) or {}
    has_stakes = isinstance(stakes_obj, dict) and bool(
        stakes_obj.get("stakes") or stakes_obj.get("stakeholders")
    )
    register = ""
    arena = ""
    stakes_list: List[str] = []
    stakeholders: List[StakeholderInfo] = []
    if isinstance(stakes_obj, dict):
        register = str(stakes_obj.get("rhetorical_register", "") or "").strip()
        arena = str(stakes_obj.get("discursive_arena", "") or "").strip()
        for s in stakes_obj.get("stakes", []) or []:
            if isinstance(s, dict):
                desc = s.get("description") or s.get("stake_type") or ""
                if desc:
                    stakes_list.append(_truncate(desc, _STAKE_CAP))
            elif isinstance(s, str) and s:
                stakes_list.append(_truncate(s, _STAKE_CAP))
        for sh in stakes_obj.get("stakeholders", []) or []:
            if isinstance(sh, dict):
                role = str(sh.get("role") or sh.get("name") or sh.get("id") or "")
                interest = (
                    sh.get("interest")
                    or sh.get("description")
                    or sh.get("stake")
                    or ""
                )
                if role or interest:
                    stakeholders.append(
                        StakeholderInfo(
                            role=str(role),
                            detail=_truncate(interest, _STAKEHOLDER_CAP),
                        )
                    )

    genre, genre_source = _derive_genre(state)
    families = _load_families()
    spectrum_available = bool(families)
    expected_spectrum, spectrum_general = _derive_expected_spectrum(families, genre)

    args = getattr(state, "identified_arguments", {}) or {}
    arg_count = len(args) if isinstance(args, dict) else 0

    virtuous_mode = detect_virtuous_mode(state)

    return Act1Evidence(
        metadata=metadata_view,
        genre=genre,
        genre_source=genre_source,
        stakes=stakes_list,
        rhetorical_register=register,
        discursive_arena=arena,
        has_stakes=has_stakes,
        expected_spectrum=expected_spectrum,
        spectrum_general=spectrum_general,
        spectrum_available=spectrum_available,
        stakeholders=stakeholders,
        arg_count=arg_count,
        virtuous_mode=virtuous_mode,
        deanonymized=bool(getattr(state, "deanonymized", True)),
    )


# --- the conducted prompt (spec §4 weaving rule, no template) ----------------

_OPAQUE_ID_DIRECTIVE = (
    "DISCIPLINE D'IDENTIFIANTS OPAQUES (FB-34) — OBLIGATOIRE :\n"
    "- Désigne le locuteur, l'arène, l'époque par des IDs opaques (Speaker_A,\n"
    "  era_A, State_Q…), JAMAIS par un nom réel, une date réelle ou un lieu.\n"
    "- Ne reproduis JAMAIS de passage verbatim du texte source : paraphrase le\n"
    "  cadre en une phrase qui dit quelque chose.\n"
    "- Les familles de sophismes (autorité, peur, généralisation…) sont des\n"
    "  constantes de taxonomie : tu peux les nommer comme ancrage."
)

_WEAVING_RULE = (
    "RÈGLE DE TISSAGE (spec §4) — le contrat anti-énumération :\n"
    "- L'Acte I est le SEUL acte qui peut ANTICIPER (spec §1.1) : tu dis ce\n"
    "  qu'un auditeur averti doit guetter, avant toute détection.\n"
    "- CHAQUE famille du spectre attendu doit être ancrée : dis POURQUOI elle\n"
    "  est attendue pour CE genre de discours (le contexte qui la rend probable).\n"
    "- INTERDIT : une ligne « nom + score isolé », ex. « ad verecundiam (0.8) ».\n"
    "  Ne produis JAMAIS de score entre parenthèses isolé. Le spectre est une\n"
    "  anticipation, pas un tableau de scores.\n"
    "- INTERDIT : numéroter en « Sophisme 1: » / « Argument 2: ». Rédige des\n"
    "  paragraphes thématiques en prose."
)

_FAIL_LOUD_INSTRUCTION = (
    "HONNÊTETÉ (anti-pendule #1019/#369) :\n"
    "- Si une métadonnée manque, DIS-LE explicitement (« registre non renseigné »),\n"
    "  ne l'invente JAMAIS.\n"
    "- Le spectre est soit dérivé du genre, soit général (genre inconnu) — la\n"
    "  note ci-dessous dit lequel. Ne prétends pas une dérivation que tu n'as pas."
)


def build_act1_prompt(evidence: Act1Evidence) -> str:
    """Build the §4-compliant LLM-conducted prompt for the Acte I framing.

    The prompt varies with the evidence (hence with the corpus) — it is not a
    static template (#1108/#405).
    """
    # --- Mode vertueux (spec §5) — anticipation qui ne se concrétise pas ---
    vm = evidence.virtuous_mode
    is_virtuous = vm is not None and vm.is_virtuous
    if is_virtuous:
        virtuous_section = (
            "MODE VIRTUEUX (spec §5) — ANTICIPATION QUI NE DÉRAPE PAS :\n"
            "Ce texte est caractérisé comme vertueux par le pipeline (zéro\n"
            "sophisme localisé + vertus mesurées). Le spectre ci-dessous reste ce\n"
            "qu'un auditeur averti GUILLETAIT pour ce genre — mais le texte ne\n"
            "dérape pas : l'anticipation ne s'est pas concrétisée. Cadre donc le\n"
            "spectre comme « ce qui aurait pu déraper et ne dérape pas », en\n"
            "honnêteté avec ce qui tient (vertus, robustesse formelle). Ne\n"
            "fabrique JAMAIS de sophisme pour valider l'attente.\n"
            f"Dérivation du flag : {vm.reasoning if vm is not None else ''}\n\n"
        )
        spectrum_coda = (
            " Sur un texte vertueux, ces familles sont l'attente NON concrétisée "
            "— dis ce qui aurait pu déraper et ne dérape pas."
        )
    else:
        virtuous_section = ""
        spectrum_coda = ""

    # --- Le texte (metadata) ---
    if evidence.metadata:
        meta_block = "\n".join(
            f"  - {k} : {v}" for k, v in evidence.metadata.items()
        )
    else:
        meta_block = "  (aucune métadonnée renseignée — contexte limité au texte analysé)"

    # --- Les enjeux ---
    if evidence.has_stakes:
        stakes_lines = [f"  - {_truncate(s, _STAKE_CAP)}" for s in evidence.stakes] or [
            "  - (enjeux présents mais non décrits)"
        ]
        stakes_block = "\n".join(stakes_lines)
        if evidence.rhetorical_register:
            stakes_block += f"\n  Registre rhétorique : {evidence.rhetorical_register}"
        if evidence.discursive_arena:
            stakes_block += f"\n  Arène discursive : {evidence.discursive_arena}"
    else:
        stakes_block = "  (enjeux non extraits — cadrage limité au microscope interne)"

    # --- Spectre attendu (derived) ---
    if not evidence.spectrum_available:
        spectrum_block = (
            "  (taxonomie non chargée — spectre anticipé indisponible ; lire "
            "l'Acte II sans filet d'attente)"
        )
        spectrum_note = "Spectre : INDISPONIBLE (taxonomie non chargée)."
    elif evidence.spectrum_general:
        spectrum_block = "\n".join(
            f"  - {f.name_fr} (sévérité {f.severity_weight:.1f})"
            for f in evidence.expected_spectrum
        )
        spectrum_note = (
            "Spectre : GÉNÉRAL (genre non renseigné → toutes les familles, "
            "ordre de sévérité). Dis-le honnêtement : on ne sait pas quel "
            "genre c'est, donc on guette large."
        )
    else:
        spectrum_block = "\n".join(
            f"  - {f.name_fr} — contexte(s) attendu(s) : {', '.join(f.matched_contexts)}"
            for f in evidence.expected_spectrum
        )
        spectrum_note = (
            f"Spectre : DÉRIVÉ du genre « {evidence.genre} » (source : "
            f"{evidence.genre_source}). Ces familles sont attendues POUR CE "
            f"genre — ancre chacune sur le contexte qui la rend probable."
        )

    # --- Game-theoretic ---
    if evidence.stakeholders:
        gt_block = "\n".join(
            f"  - {_truncate(sh.role, _STAKEHOLDER_CAP)}"
            + (f" : {sh.detail}" if sh.detail else "")
            for sh in evidence.stakeholders
        )
    else:
        gt_block = "  (parties engagées non extraites — cadrage stratégique limité)"
    gt_note = (
        f"Inventaire argumentatif : {evidence.arg_count} argument(s) extrait(s)."
    )

    opaque_block = f"{_OPAQUE_ID_DIRECTIVE}\n\n" if not evidence.deanonymized else ""

    return (
        "Tu es l'auteur de l'ACTE I d'un rapport de restitution argumentative —\n"
        "la MISE EN SITUATION, tout le cadrage AVANT d'entrer dans le texte pour\n"
        "rendre l'analyse (Acte II) lisible. Quatre battements en prose :\n"
        "1. Le texte (genre, locuteur, canal, contexte) ; 2. Les enjeux (ce qui\n"
        "se joue, pour qui, quelle asymétrie) ; 3. Le spectre des sophismes\n"
        "attendus pour ce genre (anticipation dérivée de la taxonomie) ;\n"
        "4. La lecture game-theoretic (joueurs, intérêts, coups attendus).\n\n"
        f"{opaque_block}"
        f"{_WEAVING_RULE}\n\n"
        f"{_FAIL_LOUD_INSTRUCTION}\n\n"
        f"{virtuous_section}"
        "DONNÉES VERIFIÉES DANS LE STATE :\n\n"
        f"[LE TEXTE — métadonnées]\n{meta_block}\n\n"
        f"[LES ENJEUX]\n{stakes_block}\n\n"
        f"[SPECTRE ATTENDU — dérivation taxonomie]\n{spectrum_note}{spectrum_coda}\n"
        f"{spectrum_block}\n\n"
        f"[LECTURE GAME-THEORETIC]\n{gt_block}\n{gt_note}\n\n"
        "CONSIGNE DE RÉDACTION :\n"
        "- Rédige 4 paragraphes thématiques (un par battement), en prose lisible,\n"
        "  pas une liste de champs.\n"
        "- Pour le spectre, ancre chaque famille sur le contexte qui la rend\n"
        "  probable pour ce genre (ex. « dans un discours politique, l'appel à\n"
        "  l'autorité et l'attaque personnelle sont à guetter car… »).\n"
        "- Le récit doit VARIER selon le contenu réel ci-dessus : pas de prose\n"
        "  générique recyclable.\n"
        "- Rédige en français, markdown léger (titres thématiques en ###). "
        "300-600 mots selon la richesse réelle.\n"
    )


# --- LLM-conducted weaving (fail-loud) ---------------------------------------


async def weave_act1_framing(
    evidence: Act1Evidence, llm_callable: LlmCallable
) -> str:
    """Conduct the Acte I framing via the LLM (fail-loud, #1108)."""
    prompt = build_act1_prompt(evidence)
    try:
        raw = await llm_callable(prompt)
    except Exception as exc:  # noqa: BLE001 — surface, don't fabricate
        logger.warning("Acte I LLM weaving failed (fail-loud): %s", exc)
        return ""
    if not raw:
        return ""
    return str(raw).strip()


# --- orchestrator ------------------------------------------------------------


async def build_act1_framing(
    state: Any, llm_callable: Optional[LlmCallable] = None
) -> Act1Result:
    """Build the Acte I framing narrative for ``state``.

    Deterministic evidence is always built. The narrative is LLM-conducted only
    when ``llm_callable`` is provided; otherwise fail-loud (``unavailable``,
    empty narrative) — the renderer reports the gap honestly (#1108).

    A §4 self-check (``ReadabilityGate``) is attached to every woven result so
    the verdict is auditable; it never fabricates a pass.
    """
    evidence = build_act1_evidence(state)

    # Acte I can be produced even with empty metadata (framing degrades to
    # "contexte limité au texte") — but not without an LLM to conduct it.
    if llm_callable is None:
        return Act1Result(
            narrative="",
            status="unavailable",
            degraded={
                "act1_framing": (
                    "Cadrage non conduit — aucun LLM injecté pour l'Acte I "
                    "(fail-loud, #1108)."
                )
            },
        )

    narrative = await weave_act1_framing(evidence, llm_callable)
    if not narrative:
        return Act1Result(
            narrative="",
            status="unavailable",
            degraded={
                "act1_framing": (
                    "Cadrage indisponible — le LLM n'a rien produit (fail-loud, "
                    "#1108)."
                )
            },
        )

    gate = ReadabilityGate()
    verdict = gate.check_body(narrative)
    degraded: Dict[str, str] = {}
    if verdict.band != "PASS":
        degraded["act1_framing_gate"] = (
            f"Self-check §4 = {verdict.band}: " + "; ".join(verdict.reasons[:3])
        )
    if not evidence.has_stakes:
        degraded["act1_framing"] = (
            "Enjeux non extraits (stakes_and_stakeholders vide) — cadrage "
            "limité au microscope interne, fail-loud."
        )
    if not evidence.spectrum_available:
        degraded["act1_framing_spectrum"] = (
            "Spectre attendu indisponible (taxonomie non chargée) — lire "
            "l'Acte II sans filet d'attente."
        )
    vm = evidence.virtuous_mode
    is_virtuous = vm is not None and vm.is_virtuous
    if vm is not None and vm.is_virtuous:
        degraded["act1_virtuous_mode"] = (
            "Mode vertueux (spec §5) — spectre lu comme anticipation qui ne "
            "dérape pas. " + vm.reasoning
        )

    return Act1Result(
        narrative=narrative,
        status="woven",
        gate_verdict=verdict,
        degraded=degraded,
        is_virtuous=is_virtuous,
    )
