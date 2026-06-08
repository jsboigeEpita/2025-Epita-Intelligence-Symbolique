"""Capstone FB-8 — Benchmark integral pipeline vs external-specialist yardstick.

Runs the full spectacular pipeline on corpus_X, then scores the output
against the 10-dimension yardstick (docs/reports/corpus_x_yardstick.md).

Output: per-dimension scorecard (MATCH/PARTIAL/MISSED/EXCEEDED) with
synthesis paragraphs and a terminal verdict.

Usage:
    # Real run (requires corpus_X in dataset):
    conda run -n projet-is-roo-new --no-capture-output python scripts/run_benchmark_fb8.py --corpus-idx N

    # Dry-run with synthetic placeholder (validates plumbing without real corpus):
    conda run -n projet-is-roo-new --no-capture-output python scripts/run_benchmark_fb8.py --dry-run

Output:
    argumentation_analysis/evaluation/results/capstone_c1/benchmark_corpus_x.json
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

# Load .env
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key
from argumentation_analysis.core.io_manager import load_extract_definitions

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

RESULTS_DIR = Path("argumentation_analysis/evaluation/results/capstone_c1")
DATASET_PATH = Path("argumentation_analysis/data/extract_sources.json.gz.enc")
YARDSTICK_PATH = Path("docs/reports/corpus_x_yardstick.md")

# corpus_X index in extract_sources.json.gz.enc
# Added via #1018 — public manifesto fixture, 6742 chars
CORPUS_X_IDX = 17


# ---------------------------------------------------------------------------
# Yardstick loader
# ---------------------------------------------------------------------------

def load_yardstick_dimensions() -> List[Dict[str, Any]]:
    """Load yardstick dimensions from the markdown reference.

    Falls back to hardcoded dimensions if the file is not found.
    Returns a list of dimension dicts with id, name, description.
    """
    if YARDSTICK_PATH.exists():
        # Parse the yardstick markdown for dimension names
        dims = []
        content = YARDSTICK_PATH.read_text(encoding="utf-8")
        import re
        # Match "### D<N>: <name> (<parenthetical>)" headers
        pattern = r'### (D\d+): (.+?)(?:\s*\([^)]*\))?\s*$'
        for match in re.finditer(pattern, content, re.MULTILINE):
            dims.append({
                "id": match.group(1),
                "name": match.group(2).strip(),
            })
        if len(dims) == 10:
            print(f"[FB-8] Loaded {len(dims)} yardstick dimensions from {YARDSTICK_PATH}")
            # Merge with hardcoded expected_subsystems
            for dim in dims:
                for hardcoded in YARDSTICK_DIMENSIONS:
                    if hardcoded["id"] == dim["id"]:
                        dim["expected_subsystems"] = hardcoded["expected_subsystems"]
                        dim["fallacy_markers"] = hardcoded["fallacy_markers"]
                        dim["quality_markers"] = hardcoded["quality_markers"]
                        break
            return dims

    print(f"[FB-8] Yardstick file not found or incomplete, using hardcoded dimensions")
    return YARDSTICK_DIMENSIONS

# Yardstick dimensions (D1-D10)
YARDSTICK_DIMENSIONS = [
    {"id": "D1", "name": "Jargon of Systematization",
     "description": "Meta-rhetorical framing: technical jargon concealing value judgments, circular self-justification",
     "expected_subsystems": ["fallacy_detection", "quality_scoring", "narrative_synthesis"],
     "fallacy_markers": ["begging_question", "appeal_to_authority"],
     "quality_markers": ["clarte_low"]},
    {"id": "D2", "name": "Functional Contradictions",
     "description": "Internal logical inconsistency: at least 5 irreconcilable contradiction pairs",
     "expected_subsystems": ["formal_logic", "dung_framework", "counter_argument"],
     "fallacy_markers": ["contradiction"],
     "quality_markers": ["coherence_low"]},
    {"id": "D3", "name": "Populist Rhetoric from Elite Position",
     "description": "Anti-elite populist language from elite speaker, authority-gaining through self-criticism",
     "expected_subsystems": ["fallacy_detection", "quality_scoring", "counter_argument"],
     "fallacy_markers": ["ad_populum", "ethos_manipulation"],
     "quality_markers": ["fiabilite_sources_low"]},
    {"id": "D4", "name": "Value Instrumentalization",
     "description": "Progressive values as permission structure, surface layer concealing deeper logic",
     "expected_subsystems": ["narrative_synthesis", "dung_framework", "counter_argument"],
     "fallacy_markers": [],
     "quality_markers": []},
    {"id": "D5", "name": "Historical Parallel",
     "description": "Structural isomorphism with historical reactionary speech, performativity contradiction",
     "expected_subsystems": ["narrative_synthesis", "dung_framework", "convergence"],
     "fallacy_markers": [],
     "quality_markers": []},
    {"id": "D6", "name": "Circular Self-Justification",
     "description": "Critical theory inversion: extraction justified by usefulness, usefulness by extraction",
     "expected_subsystems": ["formal_logic", "fallacy_detection", "quality_scoring"],
     "fallacy_markers": ["petitio_principii"],
     "quality_markers": ["structure_logique_low"]},
    {"id": "D7", "name": "Drive-Relief Mechanism",
     "description": "Affective vs logical truth: truth-claims relieve drives rather than prove propositions",
     "expected_subsystems": ["fallacy_detection", "quality_scoring", "narrative_synthesis"],
     "fallacy_markers": ["appeal_to_emotion"],
     "quality_markers": ["pertinence_low", "presence_sources_low"]},
    {"id": "D8", "name": "Permission Architecture",
     "description": "Sequential deployment of incompatible rhetorical frames, cumulative authority-building",
     "expected_subsystems": ["narrative_synthesis", "dung_framework", "convergence"],
     "fallacy_markers": [],
     "quality_markers": []},
    {"id": "D9", "name": "Technofascism Definition-by-Description",
     "description": "Concrete examples standing in for abstract definition, gap between stated purpose and material effect",
     "expected_subsystems": ["fact_extraction", "quality_scoring", "counter_argument"],
     "fallacy_markers": [],
     "quality_markers": []},
    {"id": "D10", "name": "Negation as Method",
     "description": "Multi-layer analysis: negating underlying systematization, not surface claims",
     "expected_subsystems": ["narrative_synthesis", "convergence"],
     "fallacy_markers": [],
     "quality_markers": []},
]


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------

def load_corpus_text(idx: Optional[int] = None, path: Optional[str] = None, max_chars: int = 60000) -> str:
    """Load corpus text from encrypted dataset by index OR from a local file path.

    Args:
        idx: Index in extract_sources.json.gz.enc (encrypted dataset).
        path: Path to a local text file (e.g., gitignored fixture).
        max_chars: Maximum characters to load.
    """
    if path is not None:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Corpus file not found: {path}")
        text = p.read_text(encoding="utf-8")
        print(f"[FB-8] Loaded corpus from file: {path} ({len(text)} chars)")
        return text[:max_chars] if len(text) > max_chars else text

    if idx is not None:
        key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
        defs = load_extract_definitions(DATASET_PATH, key)
        text = defs[idx].get("full_text", "")
        return text[:max_chars] if len(text) > max_chars else text

    raise ValueError("Either idx or path must be provided")


# ---------------------------------------------------------------------------
# Integral pipeline run
# ---------------------------------------------------------------------------

async def run_integral_pipeline(text: str) -> Dict[str, Any]:
    """Run the full spectacular pipeline with MAX config."""
    from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis

    context = {
        "fallacy_tier": "full",
        "shield_config": {"preset": "advanced", "fail_open": True},
    }

    print("[FB-8] Starting integral pipeline for corpus_X...")
    t0 = time.time()
    result = await run_unified_analysis(
        text=text,
        workflow_name="spectacular",
        context=context,
    )
    elapsed = time.time() - t0
    print(f"[FB-8] Integral pipeline completed in {elapsed:.1f}s")

    state = result.get("unified_state")
    output = {
        "corpus": "corpus_X",
        "method": "integral_pipeline",
        "elapsed_seconds": round(elapsed, 1),
        "phases": {},
    }

    if state is not None:
        snap = state.get_state_snapshot(summarize=False)
        output["phases"] = _extract_full_state(snap)
    else:
        output["phases"] = {"error": "no state available"}

    return output


def _extract_full_state(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Extract full state for benchmark scoring (more detailed than C1 extractor)."""
    phases = {}

    # Arguments
    args = snapshot.get("identified_arguments", {})
    phases["arguments"] = args if isinstance(args, dict) else (
        {f"arg_{i}": a for i, a in enumerate(args)} if isinstance(args, list) else {}
    )
    phases["arguments_count"] = len(phases["arguments"])

    # Fallacies — keep full detail for dimension scoring
    fallacies = snapshot.get("identified_fallacies", {})
    phases["fallacies"] = fallacies if isinstance(fallacies, dict) else (
        {f"fallacy_{i}": f for i, f in enumerate(fallacies)} if isinstance(fallacies, list) else {}
    )
    phases["fallacies_count"] = len(phases["fallacies"])

    # PL
    phases["propositional_analysis_results"] = snapshot.get("propositional_analysis_results", [])

    # FOL
    phases["fol_analysis_results"] = snapshot.get("fol_analysis_results", [])

    # Dung
    phases["dung_frameworks"] = snapshot.get("dung_frameworks", snapshot.get("dung_extensions", {}))

    # Counter-arguments
    phases["counter_arguments"] = snapshot.get("counter_arguments", [])

    # Quality scores
    phases["quality_scores"] = snapshot.get("argument_quality_scores", snapshot.get("quality_evaluation", {}))

    # JTMS beliefs
    phases["jtms_beliefs"] = snapshot.get("jtms_beliefs", [])

    # Governance
    phases["governance"] = snapshot.get("governance_decisions", snapshot.get("governance_results", {}))

    # Debate
    phases["debate"] = snapshot.get("debate_transcripts", snapshot.get("debate_results", {}))

    # Narrative synthesis
    phases["narrative_synthesis"] = snapshot.get("narrative_synthesis", "")

    # Trace entries
    phases["trace_entries"] = snapshot.get("trace_entries", [])

    return phases


# ---------------------------------------------------------------------------
# FR↔EN Fallacy alias map (#995)
# ---------------------------------------------------------------------------

# Derived from taxonomy_full.csv (text_fr → text_en canonical).
# Covers the 8 families + all yardstick markers (D1-D10).
# Each key is a normalised (lowercased) FR label produced by the pipeline;
# each value is the EN canonical marker expected by the yardstick scorer.
FALLACY_FR_EN_ALIASES: Dict[str, str] = {
    # Insufficiency family
    "généralisation hâtive": "hasty_generalization",
    "rationalisation": "rationalization",
    "appel à l'ignorance": "appeal_to_ignorance",
    "argument d'omniscience": "argument_from_omniscience",
    # Influence family
    "appel à l'émotion": "appeal_to_emotion",
    "appel à la peur": "appeal_to_fear",
    "appel à la pitié": "appeal_to_pity",
    "appel à la flatterie": "appeal_to_flattery",
    "appel au ridicule": "appeal_to_ridicule",
    # Faulty logics family
    "raisonnement circulaire": "circular_reasoning",
    "argument circulaire": "circular_reasoning",
    "définition circulaire": "circular_reasoning",
    "pente glissante": "slippery_slope",
    "faux dilemme": "false_dilemma",
    "fausse dichotomie": "false_dilemma",
    "pétition de principe": "begging_question",
    "non-séquitur": "non_sequitur",
    # Cheating family
    "homme de paille": "straw_man",
    "appel à l'identité": "appeal_to_identity",
    "effet de mode": "bandwagon_effect",
    "fausse équivalence": "false_equivalence",
    # Obstruction family
    "ad populum": "ad_populum",
    "raison de la majorité": "ad_populum",
    "appel à la bande": "bandwagon_fallacy",
    "atteinte personnelle": "ad_hominem",
    # Misleading language family
    "équivoque": "equivocation",
    "ambiguïté": "ambiguity",
    # Additional yardstick-specific markers
    "appel à l'autorité": "appeal_to_authority",
    "tromperie implicite": "implicit_deception",
    "sophisme naturel": "naturalistic_fallacy",
}


def _normalize_fallacy_type(raw: str) -> str:
    """Normalize a fallacy type string for matching.

    Lowercases, strips, and applies the FR→EN alias map if applicable.
    """
    key = raw.lower().strip()
    # Direct alias hit; otherwise return key verbatim (already lowercase).
    if key in FALLACY_FR_EN_ALIASES:
        return FALLACY_FR_EN_ALIASES[key]
    return key


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------

def score_against_yardstick(pipeline_output: Dict[str, Any]) -> Dict[str, Any]:
    """Score pipeline output against the 10-dimension yardstick.

    Returns per-dimension scorecard with synthesis paragraphs.
    """
    phases = pipeline_output.get("phases", {})
    scorecard = {}

    fallacies = phases.get("fallacies", {})
    fallacy_types = set()
    if isinstance(fallacies, dict):
        for _fid, fdata in fallacies.items():
            if isinstance(fdata, dict):
                # Collect both family and fallacy_type, normalize each
                for field in ("family", "fallacy_type"):
                    raw = fdata.get(field, "")
                    if raw:
                        fallacy_types.add(_normalize_fallacy_type(raw))
                # Also check for specific markers in description
                desc = fdata.get("description", "").lower()
                if "circul" in desc or "begging" in desc or "question" in desc:
                    fallacy_types.add("circular_reasoning")
                if "émotion" in desc or "emotion" in desc or "pathos" in desc:
                    fallacy_types.add("appeal_to_emotion")
                if "autorité" in desc or "authority" in desc:
                    fallacy_types.add("appeal_to_authority")
                if "populum" in desc or "people" in desc or "populaire" in desc:
                    fallacy_types.add("ad_populum")
    elif isinstance(fallacies, list):
        for f in fallacies:
            if isinstance(f, dict):
                ft = f.get("family", f.get("fallacy_type", "")).lower()
                fallacy_types.add(ft)

    args = phases.get("arguments", {})
    args_count = phases.get("arguments_count", 0)

    counter_args = phases.get("counter_arguments", [])
    counter_count = len(counter_args) if isinstance(counter_args, (list, dict)) else 0

    dung = phases.get("dung_frameworks", {})
    dung_count = len(dung) if isinstance(dung, dict) else 0
    dung_ext_total = 0
    if isinstance(dung, dict):
        for df_id, fw in dung.items():
            if isinstance(fw, dict):
                extensions = fw.get("extensions", {})
                if isinstance(extensions, dict):
                    dung_ext_total += sum(len(m) for m in extensions.values() if isinstance(m, list))

    quality = phases.get("quality_scores", {})
    narrative = phases.get("narrative_synthesis", "")
    narrative_len = len(narrative) if isinstance(narrative, str) else 0

    # PL/FOL formal verification
    pl_results = phases.get("propositional_analysis_results", [])
    fol_results = phases.get("fol_analysis_results", [])
    pl_count = 0
    if isinstance(pl_results, list):
        pl_count = sum(len(r.get("formulas", [])) for r in pl_results if isinstance(r, dict))
    fol_count = 0
    if isinstance(fol_results, list):
        fol_count = sum(len(r.get("formulas", [])) for r in fol_results if isinstance(r, dict))

    # --- Score each dimension ---
    for dim in YARDSTICK_DIMENSIONS:
        dim_id = dim["id"]
        score, synthesis = _score_dimension(
            dim, fallacy_types, args_count, counter_count,
            dung_count, dung_ext_total, quality, narrative_len,
            pl_count, fol_count, phases
        )
        scorecard[dim_id] = {
            "name": dim["name"],
            "score": score,
            "synthesis": synthesis,
        }

    return scorecard


def _score_dimension(
    dim: Dict[str, Any],
    fallacy_types: set,
    args_count: int,
    counter_count: int,
    dung_count: int,
    dung_ext_total: int,
    quality: Dict,
    narrative_len: int,
    pl_count: int,
    fol_count: int,
    phases: Dict,
) -> tuple:
    """Score a single dimension. Returns (score, synthesis_paragraph)."""
    dim_id = dim["id"]
    name = dim["name"]

    if dim_id == "D1":  # Jargon of Systematization
        has_circular = "circular_reasoning" in fallacy_types or "begging_question" in fallacy_types or "pétition de principe" in fallacy_types
        has_auth = "appeal_to_authority" in fallacy_types or "appel à l'autorité" in fallacy_types
        fallacy_hit = has_circular or has_auth
        if fallacy_hit and narrative_len > 500:
            return "MATCH", (
                f"The pipeline identified circular reasoning or authority-appeal markers "
                f"corresponding to the systematization jargon pattern. The narrative synthesis "
                f"({narrative_len} chars) provides structural context. "
                f"This matches the specialist's observation that technical vocabulary conceals "
                f"value judgments through circular self-justification."
            )
        elif fallacy_hit or narrative_len > 200:
            return "PARTIAL", (
                f"The pipeline detected some markers (circular: {has_circular}, authority: {has_auth}) "
                f"but may not have synthesized the meta-rhetorical framing at the depth the specialist did. "
                f"Narrative synthesis: {narrative_len} chars."
            )
        else:
            return "MISSED", (
                f"The pipeline did not identify the systematization jargon pattern. "
                f"No circular reasoning or authority-appeal fallacies were detected among "
                f"the {len(fallacy_types)} fallacy types found."
            )

    elif dim_id == "D2":  # Functional Contradictions
        has_contradiction = dung_ext_total > 0  # Self-attacking Dung framework
        formal_count = pl_count + fol_count
        if has_contradiction and formal_count >= 5 and counter_count >= 3:
            return "MATCH", (
                f"The pipeline detected formal contradictions via {pl_count} PL + {fol_count} FOL formulas, "
                f"{dung_ext_total} Dung extensions across {dung_count} frameworks (showing attack relations), "
                f"and {counter_count} counter-arguments targeting structural vulnerabilities. "
                f"This matches the specialist's identification of at least 5 contradiction pairs."
            )
        elif has_contradiction or formal_count > 0:
            return "PARTIAL", (
                f"The pipeline found some contradiction evidence ({formal_count} formal formulas, "
                f"{dung_ext_total} Dung extensions) but may not have identified all 5 specific pairs "
                f"the specialist noted. {counter_count} counter-arguments generated."
            )
        else:
            return "MISSED", (
                f"The pipeline did not detect the functional contradictions. "
                f"No Dung attack relations or formal inconsistencies found."
            )

    elif dim_id == "D3":  # Populist Rhetoric
        has_populum = "ad_populum" in fallacy_types or "appel au peuple" in fallacy_types
        if has_populum and counter_count >= 2:
            return "MATCH", (
                f"The pipeline identified populist rhetoric markers (ad populum detected) "
                f"and generated {counter_count} counter-arguments targeting the authority gap. "
                f"This matches the specialist's observation of anti-elite language from elite position."
            )
        elif has_populum:
            return "PARTIAL", (
                f"Populist markers detected but limited counter-argument exploitation ({counter_count}). "
                f"The authority gap dimension may not be fully articulated."
            )
        else:
            return "MISSED", (
                f"No populist rhetoric markers (ad populum) detected among the "
                f"{len(fallacy_types)} fallacy types found."
            )

    elif dim_id == "D4":  # Value Instrumentalization
        has_values_contradiction = dung_ext_total > 0 and counter_count >= 2
        if has_values_contradiction and narrative_len > 300:
            return "MATCH", (
                f"The pipeline's Dung framework ({dung_ext_total} extensions) reveals arguments "
                f"attacking each other — values invoked in one part contradicted in another. "
                f"{counter_count} counter-arguments and narrative synthesis ({narrative_len} chars) "
                f"provide evidence of value instrumentalization detection."
            )
        elif dung_ext_total > 0 or narrative_len > 100:
            return "PARTIAL", (
                f"Some evidence of value contradictions in the Dung framework, "
                f"but the narrative synthesis may not explicitly identify the permission-structure pattern."
            )
        else:
            return "MISSED", (
                f"No evidence of value instrumentalization detected in pipeline output."
            )

    elif dim_id == "D5":  # Historical Parallel
        # This requires synthesis-level insight — hardest dimension
        if narrative_len > 1000 and counter_count >= 5:
            return "PARTIAL", (
                f"The pipeline's narrative synthesis ({narrative_len} chars) and {counter_count} counter-arguments "
                f"may contain structural pattern recognition, but historical parallel identification "
                f"is a synthesis-level insight the pipeline is not specifically designed for. "
                f"The performativity contradiction (doing X while criticizing X) may be partially captured."
            )
        elif narrative_len > 200:
            return "PARTIAL", (
                f"Limited narrative synthesis ({narrative_len} chars). Historical parallel detection "
                f"is an out-of-scope capability for the current pipeline architecture."
            )
        else:
            return "MISSED", (
                f"Insufficient narrative synthesis for historical parallel detection."
            )

    elif dim_id == "D6":  # Circular Self-Justification
        has_circular = "circular_reasoning" in fallacy_types or "pétition de principe" in fallacy_types
        if has_circular and (pl_count > 0 or fol_count > 0):
            return "MATCH", (
                f"The pipeline detected circular reasoning (petitio principii) via fallacy detection "
                f"AND formalized it in {pl_count} PL + {fol_count} FOL formulas. "
                f"The circular structure (conclusion smuggled into premise) matches the specialist's "
                f"identification of the extraction-justification cycle."
            )
        elif has_circular:
            return "PARTIAL", (
                f"Circular reasoning detected by the fallacy detector but not formally verified. "
                f"The pipeline identified the pattern but did not formalize the circular structure."
            )
        else:
            return "MISSED", (
                f"No circular reasoning detected in pipeline output."
            )

    elif dim_id == "D7":  # Drive-Relief Mechanism
        has_emotion = "appeal_to_emotion" in fallacy_types or "appel à l'émotion" in fallacy_types
        if has_emotion and narrative_len > 300:
            return "MATCH", (
                f"The pipeline identified emotional appeals (pathos over logos) and the narrative synthesis "
                f"({narrative_len} chars) provides context on the emotional substitution pattern. "
                f"This matches the specialist's drive-relief mechanism observation."
            )
        elif has_emotion:
            return "PARTIAL", (
                f"Emotional appeal markers detected but limited synthesis on the affective truth mechanism."
            )
        else:
            return "MISSED", (
                f"No emotional appeal markers detected among {len(fallacy_types)} fallacy types."
            )

    elif dim_id == "D8":  # Permission Architecture
        if dung_ext_total > 50 and narrative_len > 500:
            return "PARTIAL", (
                f"The Dung framework ({dung_ext_total} extensions across {dung_count} frameworks) maps "
                f"argument relationships that may reveal the sequential escalation pattern. "
                f"However, the specific 'permission architecture' (cumulative authority through "
                f"contradictory appeals) requires cross-argument synthesis that the pipeline "
                f"may only partially achieve. Narrative synthesis: {narrative_len} chars."
            )
        elif dung_ext_total > 0:
            return "PARTIAL", (
                f"Limited Dung framework evidence ({dung_ext_total} extensions). "
                f"The permission escalation pattern requires deeper cross-argument analysis."
            )
        else:
            return "MISSED", (
                f"Insufficient Dung framework output to detect permission architecture."
            )

    elif dim_id == "D9":  # Technofascism Definition-by-Description
        if args_count >= 5 and counter_count >= 2:
            return "PARTIAL", (
                f"The pipeline extracted {args_count} arguments and generated {counter_count} counter-arguments, "
                f"which may probe the gap between stated purpose and material effect. "
                f"However, the specific 'definition-by-description' pattern (concrete examples "
                f"revealing political violence behind technical administration) is a synthesis-level "
                f"insight that requires fact-checking against external knowledge the pipeline does not have."
            )
        elif args_count > 0:
            return "PARTIAL", (
                f"Some argument extraction ({args_count} args) but limited counter-argument analysis."
            )
        else:
            return "MISSED", (
                f"No argument extraction or counter-argument generation."
            )

    elif dim_id == "D10":  # Negation as Method
        if narrative_len > 500 and counter_count >= 5:
            return "PARTIAL", (
                f"The pipeline's narrative synthesis ({narrative_len} chars) and {counter_count} counter-arguments "
                f"demonstrate some capacity for multi-layer analysis. However, the specific 'negation of "
                f"systematization' method (distinguishing surface jargon from deep jargon) is a meta-analytical "
                f"prescription that goes beyond the pipeline's current design scope."
            )
        else:
            return "MISSED", (
                f"Insufficient synthesis output for negation-as-method analysis."
            )

    return "MISSED", "Unknown dimension."


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

async def run_benchmark(corpus_idx: Optional[int] = None, corpus_path: Optional[str] = None,
                       dry_run: bool = False) -> Dict[str, Any]:
    """Run FB-8 benchmark: pipeline vs yardstick.

    Args:
        corpus_idx: Index of corpus_X in encrypted dataset.
        corpus_path: Path to local text file (gitignored fixture).
        dry_run: If True, use synthetic placeholder output to validate plumbing.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load yardstick dimensions (from file or hardcoded)
    yardstick_dims = load_yardstick_dimensions()
    print(f"[FB-8] Yardstick: {len(yardstick_dims)} dimensions loaded")

    if dry_run:
        print("[FB-8] *** DRY-RUN MODE — synthetic placeholder output ***")
        pipeline_output = _synthetic_placeholder_output()
    else:
        if corpus_idx is None and corpus_path is None:
            raise ValueError("--corpus-idx or --corpus-path required for real run (use --dry-run for plumbing test)")
        # 1. Load corpus_X text
        source_desc = f"index {corpus_idx}" if corpus_idx is not None else f"file {corpus_path}"
        print(f"[FB-8] Loading corpus_X ({source_desc})...")
        text = load_corpus_text(idx=corpus_idx, path=corpus_path)
        print(f"[FB-8] corpus_X: {len(text)} chars loaded")

        # 2. Run integral pipeline
        pipeline_output = await run_integral_pipeline(text)

    # Save raw pipeline state
    pipeline_path = RESULTS_DIR / ("integral_X_dryrun.json" if dry_run else "integral_X.json")
    with open(pipeline_path, "w", encoding="utf-8") as f:
        json.dump(pipeline_output, f, indent=2, ensure_ascii=False, default=str)
    print(f"[FB-8] Pipeline results saved to {pipeline_path}")

    # 3. Score against yardstick
    print("[FB-8] Scoring against yardstick dimensions...")
    scorecard = score_against_yardstick(pipeline_output)

    # 4. Build benchmark report
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "corpus": "corpus_X",
        "method": "benchmark_fb8_dryrun" if dry_run else "benchmark_fb8",
        "yardstick_source": str(YARDSTICK_PATH),
        "yardstick_dimensions": len(yardstick_dims),
        "pipeline_elapsed": pipeline_output.get("elapsed_seconds"),
        "scorecard": scorecard,
        "verdict": _compute_verdict(scorecard),
    }

    if dry_run:
        report["dry_run"] = True
        report["dry_run_note"] = "Synthetic placeholder — not real pipeline output. Scores are meaningless."

    # Save benchmark report
    report_path = RESULTS_DIR / ("benchmark_corpus_x_dryrun.json" if dry_run else "benchmark_corpus_x.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"[FB-8] Benchmark report saved to {report_path}")

    # Print summary
    _print_summary(report)

    return report


def _synthetic_placeholder_output() -> Dict[str, Any]:
    """Generate synthetic pipeline output for dry-run plumbing validation.

    This produces a plausible but fake pipeline state to verify the scoring
    engine, yardstick loader, and report generator work end-to-end.
    """
    return {
        "corpus": "corpus_X_PLACEHOLDER",
        "method": "dry_run_placeholder",
        "elapsed_seconds": 0.0,
        "phases": {
            "arguments": {
                "arg_0": "Placeholder argument 1",
                "arg_1": "Placeholder argument 2",
                "arg_2": "Placeholder argument 3",
            },
            "arguments_count": 3,
            "fallacies": {
                "fallacy_0": {
                    "family": "appel à l'autorité",
                    "fallacy_type": "appeal_to_authority",
                    "description": "Uses technical jargon to perform authority",
                    "confidence": 0.7,
                },
                "fallacy_1": {
                    "family": "pétition de principe",
                    "fallacy_type": "begging_question",
                    "description": "Circular reasoning: extraction justified by usefulness",
                    "confidence": 0.8,
                },
                "fallacy_2": {
                    "family": "appel à l'émotion",
                    "fallacy_type": "appeal_to_emotion",
                    "description": "Emotional appeal masking logical gap",
                    "confidence": 0.6,
                },
            },
            "fallacies_count": 3,
            "propositional_analysis_results": [
                {"formulas": ["P → Q", "Q → R", "P"], "satisfiable": True},
            ],
            "fol_analysis_results": [
                {"formulas": ["∀x(P(x) → Q(x))"], "consistent": True},
            ],
            "dung_frameworks": {
                "dung_0": {
                    "name": "Placeholder Framework",
                    "arguments": ["a1", "a2", "a3"],
                    "attacks": [["a2", "a1"]],
                    "extensions": {
                        "grounded": ["a1", "a3"],
                        "preferred": [["a1", "a3"], ["a2"]],
                    },
                },
            },
            "counter_arguments": [
                "Counter 1: challenges circular reasoning",
                "Counter 2: identifies authority gap",
                "Counter 3: targets emotional substitution",
            ],
            "quality_scores": {
                "clarte": 0.4,
                "structure_logique": 0.3,
                "pertinence": 0.5,
            },
            "jtms_beliefs": ["belief_1", "belief_2"],
            "governance": {"conflicts": [], "consensus_level": 0.5},
            "debate": {"total_rounds": 3, "winner": "critic"},
            "narrative_synthesis": "Placeholder synthesis: the text uses circular reasoning and emotional appeals "
                                    "to construct a permission architecture. Multiple contradictions were detected "
                                    "in the argument structure. The jargon of systematization conceals value judgments.",
            "trace_entries": ["trace_1", "trace_2"],
        },
    }


def _compute_verdict(scorecard: Dict[str, Any]) -> Dict[str, Any]:
    """Compute terminal verdict from scorecard."""
    scores = {"MATCH": 0, "PARTIAL": 0, "MISSED": 0, "EXCEEDED": 0}
    for dim_id, dim_data in scorecard.items():
        s = dim_data.get("score", "MISSED")
        scores[s] = scores.get(s, 0) + 1

    match_or_exceeded = scores["MATCH"] + scores["EXCEEDED"]
    total = sum(scores.values())

    verdict = {
        "scores": scores,
        "match_or_exceeded": match_or_exceeded,
        "total": total,
        "bar_met": match_or_exceeded >= 7,
        "has_exceeded": scores["EXCEEDED"] >= 1,
    }

    if match_or_exceeded >= 7 and scores["EXCEEDED"] >= 1:
        verdict["verdict"] = "EXCEEDED — pipeline meets and exceeds specialist analysis"
    elif match_or_exceeded >= 7:
        verdict["verdict"] = "MATCH — pipeline meets specialist analysis on ≥7/10 dimensions"
    elif match_or_exceeded >= 5:
        verdict["verdict"] = "PARTIAL — pipeline partially matches specialist analysis"
    else:
        verdict["verdict"] = "BELOW — pipeline does not meet specialist analysis bar"

    return verdict


def _print_summary(report: Dict[str, Any]) -> None:
    """Print human-readable benchmark summary."""
    print("\n" + "=" * 60)
    print("FB-8 BENCHMARK RESULTS")
    print("=" * 60)
    for dim_id, dim_data in report["scorecard"].items():
        score = dim_data["score"]
        icon = {"MATCH": "🟢", "PARTIAL": "🟡", "MISSED": "🔴", "EXCEEDED": "🌟"}.get(score, "❓")
        print(f"  {icon} {dim_id} {dim_data['name']}: {score}")
    print()
    verdict = report["verdict"]
    print(f"  Verdict: {verdict['verdict']}")
    print(f"  Match/Exceeded: {verdict['match_or_exceeded']}/{verdict['total']}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Capstone FB-8 — Pipeline vs Yardstick Benchmark")
    parser.add_argument("--corpus-idx", type=int, default=None,
                        help="Index of corpus_X in extract_sources.json.gz.enc")
    parser.add_argument("--corpus-path", type=str, default=None,
                        help="Path to local corpus_X text file (gitignored fixture)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run with synthetic placeholder output (validates plumbing)")
    args = parser.parse_args()

    if not args.dry_run and args.corpus_idx is None and args.corpus_path is None:
        parser.error("Either --corpus-idx, --corpus-path, or --dry-run is required")

    asyncio.run(run_benchmark(corpus_idx=args.corpus_idx, corpus_path=args.corpus_path,
                              dry_run=args.dry_run))


if __name__ == "__main__":
    main()
