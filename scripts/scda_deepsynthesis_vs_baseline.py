"""DeepSynthesis vs LLM 0-shot baseline comparison (#592).

Runs the full SCDA pipeline (producing DeepSynthesis report) alongside a
direct LLM 0-shot analysis, then compares on measurable dimensions.

Usage:
    python scripts/scda_deepsynthesis_vs_baseline.py --corpus A
    python scripts/scda_deepsynthesis_vs_baseline.py --corpus all

Outputs: outputs/deep_analysis/ (gitignored)
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

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

CORPORA = {
    "A": {"src_idx": 11, "label": "corpus_dense_A", "desc": "EN dense (~58K)"},
    "B": {"src_idx": 3, "label": "corpus_dense_B", "desc": "DE dense (~50K)"},
    "C": {"src_idx": 2, "label": "corpus_dense_C", "desc": "EN dense (~46K)"},
}

OUTPUTS_DIR = Path("outputs/deep_analysis")

BASELINE_PROMPT = """Analyse rhétorique complète du texte suivant. Identifie les sophismes, structures argumentatives, contre-arguments potentiels, incohérences logiques. Output : analyse markdown structurée par dimension.

Pour chaque dimension, fournis:
1. **Sophismes détectés** — nom du sophisme avec chemin taxonomique (ex: Appel à l'autorité > Autorité non pertinente)
2. **Structures argumentatives** — prémisses, conclusions, liens logiques
3. **Contre-arguments** — au moins un contre-argument par argument principal
4. **Incohérences logiques** — contradictions internes, affirmations non supportées
5. **Vérification formelle** — toute analyse utilisant des méthodes formelles (logique propositionnelle, FOL, cadres de Dung, ASPIC+)
6. **Citations textuelles** — extraits exacts du texte source

Texte à analyser:
"""


def load_corpus(corpus_id: str) -> str:
    """Load text for a given corpus."""
    info = CORPORA[corpus_id]
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(
        Path("argumentation_analysis/data/extract_sources.json.gz.enc"), key
    )
    src = defs[info["src_idx"]]
    text = src.get("full_text", "")

    if corpus_id == "B":
        speech_markers = re.split(r"(?=\d{4}\.\d{2}\.\d{2})", text)
        best_chunk = ""
        for chunk in speech_markers:
            if 30000 <= len(chunk) <= 60000:
                if len(chunk) > len(best_chunk):
                    best_chunk = chunk
        if not best_chunk:
            start = len(text) // 4
            boundary = text.find("\n\n", start)
            if boundary > 0:
                start = boundary
            best_chunk = text[start : start + 50000]
        text = best_chunk

    return text


def count_textual_citations(text: str) -> int:
    """Count quoted text excerpts in a report."""
    # Match quoted passages, citation markers, "..." quoted segments
    patterns = [
        r'"[^"]{10,}"',  # Double-quoted passages >= 10 chars
        r"'[^']{10,}'",  # Single-quoted passages
        r"«[^»]{10,}»",  # French quotes
        r"\*\*Citation\*\*:.*",  # Explicit citation markers
        r"> .{10,}",  # Block quotes
    ]
    count = 0
    for pat in patterns:
        count += len(re.findall(pat, text, re.DOTALL))
    return count


def count_named_fallacies_with_taxonomy(text: str) -> list[dict]:
    """Extract named fallacies with taxonomy paths.

    Covers standard FR/EN names AND taxonomy-specific names emitted by the
    pipeline's hierarchical detector (e.g. Enthymême invalide, Appel au
    racisme, Tromperie implicite). Extended for Track PP (#665) so the
    benchmark measures what the pipeline actually names, not just a fixed
    set of 34 standard labels.
    """
    fallacy_families = [
        # Standard FR/EN names
        "Appel à l'autorité",
        "Appel a l'autorite",
        "Appeal to authority",
        "Appel à la popularité",
        "Appel a la popularite",
        "Bandwagon",
        "Appel à l'émotion",
        "Appeal to emotion",
        "Attaque personnelle",
        "Ad hominem",
        "Pente glissante",
        "Slippery slope",
        "Faux dilemme",
        "False dilemma",
        "Black and white",
        "Homme de paille",
        "Straw man",
        "Pétition de principe",
        "Begging the question",
        "Circular reasoning",
        "Hasty generalization",
        "Généralisation hâtive",
        "Post hoc",
        "Corrélation causale",
        "Non sequitur",
        "Appel à l'ignorance",
        "Appeal to ignorance",
        "Fausse équivalence",
        "False equivalence",
        "Red herring",
        "Hareng rouge",
        "Tu quoque",
        "Cherry picking",
        "Reductio ad absurdum",
        # Taxonomy-specific names emitted by the pipeline detector
        "Enthymême invalide",
        "Appel au racisme",
        "Appel à la panique morale",
        "Tromperie implicite",
        "Illusion de regroupement",
        "Sophisme du faisceau de preuves",
        "Argument du package",
        "Appel à la temporalité",
        "Sophisme de la cause unique",
        "Sophisme de portée modale",
        "Pseudorationalisme",
        "Culpabilité par association",
        "Empoisonnement du puits",
        "Appel au peuple",
        "Simplification excessive",
        "Faux espoir",
        "Appel à la tradition",
        "Appel à la nouveauté",
        "Sophisme génétique",
        "Généralisation abusive",
        "Argumentum ad populum",
        "Argumentum ad consequentiam",
        "Sophisme naturaliste",
        "Is-ought",
        "Appel à la pitié",
        "Appel à la peur",
        "Menace voilée",
        "Discours de haine",
        "Démonisation",
        "Stigmatisation",
        # Additional taxonomy names from pipeline reports (corpus B/C)
        "Appel au nationalisme",
        "Appel à l'identité nationale",
        "Appel au drapeau rouge",
        "Reductio ad Hitlerum",
        "Amalgame",
        "Cécité d'inattention",
        "Argument par l'insinuation",
        "Théorie du complot",
        "Hyperbole",
    ]
    found = []
    lines = text.lower()
    for fallacy in fallacy_families:
        if fallacy.lower() in lines:
            found.append(
                {
                    "name": fallacy,
                    "has_taxonomy": ">" in text or "/" in text or ":" in text,
                }
            )
    return found


def count_fallacy_families(text: str) -> dict:
    """Count distinct fallacy families (causal, relevance, presumption, inductive, ambiguity).

    Parses the Section 3 headers of the DeepSynthesis report which use the format:
    ``### fallacy_N: family — `fallacy/family/Name````
    """
    families = {
        "causal": 0,
        "relevance": 0,
        "presumption": 0,
        "inductive": 0,
        "ambiguity": 0,
        "other": 0,
    }
    for line in text.splitlines():
        if line.startswith("### fallacy_"):
            m = re.match(r"### fallacy_\d+:\s*(\w+)", line)
            if m:
                family = m.group(1).lower()
                if family in families:
                    families[family] += 1
                else:
                    families["other"] += 1
    return families


def detect_formal_method_findings(text: str) -> dict:
    """Check for formal method markers in report."""
    markers = {
        "tweety_kb": any(
            kw in text.lower()
            for kw in [
                "tweety",
                "belief set",
                "ensemble de croyances",
                "pl satisfiability",
            ]
        ),
        "dung_extensions": any(
            kw in text.lower()
            for kw in ["dung", "extension", "attaque", "framework", "cadre de dung"]
        ),
        "aspic_inconsistency": any(
            kw in text.lower()
            for kw in ["aspic", "inconsistance", "defeasible", "strict rule"]
        ),
        "fol_analysis": any(
            kw in text.lower()
            for kw in [
                "first-order logic",
                "fol",
                "logique du premier ordre",
                "prédicat",
                "quantifie",
            ]
        ),
        "pl_analysis": any(
            kw in text.lower()
            for kw in ["propositional", "pl ", "logique propositionnelle", "sat solver"]
        ),
        "modal_analysis": any(
            kw in text.lower()
            for kw in ["modal logic", "modalité", "nécessairement", "possibly"]
        ),
        "agm_revision": any(
            kw in text.lower()
            for kw in ["agm", "belief revision", "rétractation", "contraction"]
        ),
    }
    return {k: v for k, v in markers.items() if v}


def detect_cross_text_parallels(text: str) -> bool:
    """Check for *populated* intertextual/cross-corpus references.

    The section heading "Cross-Text Rhetorical Parallels" must not by itself
    count as a parallel: the DeepSynthesis report always emits the heading, even
    when the body says "No cross-text parallels in this run". Guard against that
    explicit-negation false-positive, then look for substantive markers only
    (the heading-matching "cross-text"/"cross text" tokens are excluded).
    """
    low = text.lower()
    if re.search(r"no cross-text parallels|pas de parall|aucun parall", low):
        return False
    markers = [
        "intertextuel",
        "parallèle",
        "comparison with",
        "similar to",
        "pattern also found",
        "comparaison avec",
        "similaire à",
        "pattern également",
        "récurrence",
        "motif récurrent",
    ]
    return any(m in low for m in markers)


def count_convergence_depth(text: str) -> dict:
    """Count cross-method convergent verdicts in a report.

    A convergent verdict — "N independent methods concur on arg_X" — is the one
    artifact a single LLM pass structurally cannot fabricate: it requires several
    independent solvers (fallacy / quality / counter-arg / JTMS / Dung) to be run
    and their agreement tallied. Parsed from the "Convergent Verdicts" section.
    """
    # e.g. "**Verdict convergent sur arg_1** : 5 methodes independantes ..."
    pattern = re.compile(
        r"verdict convergent sur\s+([\w-]+)\D*?(\d+)\s*m[ée]thodes",
        re.IGNORECASE,
    )
    matches = pattern.findall(text)
    scores = [int(n) for _, n in matches]
    return {
        "verdict_count": len(scores),
        "max_convergence": max(scores) if scores else 0,
        "total_method_signals": sum(scores),
    }


def detect_computed_artifacts(text: str) -> dict:
    """Detect *computed* (not merely described) formal artifacts.

    These require concrete solver output — a membership set, an edge list, a
    numeric measure, a retraction count. A 0-shot that describes Dung/ASPIC in
    the abstract emits none of them, so they cannot be name-dropped into a win.
    """
    low = text.lower()
    artifacts = {}

    # (a) Grounded-extension *membership set*: an explicit list of arg ids tied
    #     to the grounded extension (not just the phrase "grounded extension").
    if re.search(r"grounded extension[^\n]*?(?:contains|:)[^\n]*?\barg_?\d+", low):
        artifacts["grounded_extension_members"] = True

    # (b) Attack *edge list*: concrete attacker → target relations.
    edge_count = len(re.findall(r"`[^`]+`\s*(?:→|->)\s*`?arg_?\d+", text))
    if edge_count == 0:
        edge_count = len(re.findall(r"→\s*arg_?\d+", text))
    if edge_count > 0:
        artifacts["attack_edge_list"] = edge_count

    # (c) Numeric inconsistency / framework measures (a number attached to a
    #     formal measure, e.g. "11 surviving", "inconsistency: 0.4").
    if re.search(r"(?:inconsisten|inconsistan)\w*[^\n]*?\d", low) or re.search(
        r"\d+\s+(?:surviving|defeated|strict|defeasible)\b", low
    ):
        artifacts["inconsistency_measures"] = True

    # (d) JTMS retraction / belief-contraction *count*.
    m = re.search(r"(\d+)\s+(?:beliefs?\s+)?(?:contracted|retract\w*)", low)
    if m and int(m.group(1)) > 0:
        artifacts["jtms_retraction_count"] = int(m.group(1))

    return artifacts


def analyze_report(text: str) -> dict:
    """Run all dimension analyses on a report."""
    return {
        "textual_citations": count_textual_citations(text),
        "named_fallacies": count_named_fallacies_with_taxonomy(text),
        "fallacy_families": count_fallacy_families(text),
        "formal_method_findings": detect_formal_method_findings(text),
        "has_cross_text_parallels": detect_cross_text_parallels(text),
        "convergence": count_convergence_depth(text),
        "computed_artifacts": detect_computed_artifacts(text),
        "word_count": len(text.split()),
        "section_count": len(re.findall(r"^#{1,3}\s", text, re.MULTILINE)),
    }


async def run_baseline_0shot(text: str, model: str = "gpt-4o-mini") -> str:
    """Run a direct LLM 0-shot analysis."""
    import openai

    client = openai.OpenAI()

    # Truncate to ~30K chars to fit context window
    truncated = text[:30000]
    if len(text) > 30000:
        truncated += "\n\n[... texte tronqué ...]"

    # gpt-5 family rejects `max_tokens` (needs `max_completion_tokens`) and
    # non-default `temperature`; fall back gracefully for older models.
    messages = [
        {
            "role": "system",
            "content": "Tu es un expert en analyse rhétorique et en logique formelle.",
        },
        {"role": "user", "content": BASELINE_PROMPT + truncated},
    ]
    # gpt-5 reasoning models spend completion tokens on hidden reasoning before
    # any visible output, so the budget must be generous or the answer comes back
    # empty. 16384 leaves ample room for a full analysis after reasoning.
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=16384,
        )
    except openai.BadRequestError:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=4096,
        )
    return response.choices[0].message.content


async def run_comparison(corpus_id: str, skip_pipeline: bool = False) -> dict:
    """Run full comparison for one corpus."""
    info = CORPORA[corpus_id]
    print(f"\n{'='*60}")
    print(f"DeepSynthesis vs Baseline — {info['label']} ({info['desc']})")
    print(f"{'='*60}")

    text = load_corpus(corpus_id)
    print(f"Loaded {len(text):,} chars")

    out_dir = OUTPUTS_DIR / info["label"]
    out_dir.mkdir(parents=True, exist_ok=True)

    model = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-4o-mini")
    results = {}

    # Step 1: Run full SCDA pipeline → DeepSynthesis report
    if not skip_pipeline:
        print("\n--- Step 1: Running full SCDA pipeline ---")
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            run_conversational_analysis,
        )

        start = time.time()
        pipeline_result = await run_conversational_analysis(
            text=text,
            max_turns_per_phase=10,
            spectacular=True,
        )
        pipeline_duration = time.time() - start
        print(f"Pipeline completed in {pipeline_duration:.1f}s")

        state = pipeline_result.get("unified_state")
        deep_synth_data = pipeline_result.get("deep_synthesis") or {}
        deepsynth_report = deep_synth_data.get("markdown", "")
        conversation_log = pipeline_result.get("conversation_log", [])

        if deepsynth_report:
            with open(out_dir / "deepsynth_report.md", "w", encoding="utf-8") as f:
                f.write(deepsynth_report)
            print(f"DeepSynthesis report saved ({len(deepsynth_report)} chars)")
        else:
            deepsynth_report = ""
            print("WARNING: No DeepSynthesis report generated")

        # Also save state for reference
        if state and hasattr(state, "get_state_snapshot"):
            snap = state.get_state_snapshot(summarize=True)
            with open(out_dir / "pipeline_state.json", "w", encoding="utf-8") as f:
                json.dump(snap, f, indent=2, ensure_ascii=False, default=str)

        with open(out_dir / "pipeline_conversation.json", "w", encoding="utf-8") as f:
            json.dump(conversation_log, f, indent=2, ensure_ascii=False, default=str)

        results["pipeline_duration"] = round(pipeline_duration, 1)
        results["pipeline_turns"] = len(conversation_log)
        results["deepsynth_word_count"] = (
            len(deepsynth_report.split()) if deepsynth_report else 0
        )
    else:
        print("\n--- Step 1: SKIPPED (using cached results) ---")
        # Try to load cached
        cached_report = out_dir / "deepsynth_report.md"
        deepsynth_report = (
            cached_report.read_text(encoding="utf-8") if cached_report.exists() else ""
        )
        results["pipeline_duration"] = "cached"
        results["pipeline_turns"] = "cached"

    # Step 2: Run 0-shot baseline
    print(f"\n--- Step 2: Running 0-shot baseline ({model}) ---")
    start = time.time()
    baseline_report = await run_baseline_0shot(text, model=model)
    baseline_duration = time.time() - start
    print(f"Baseline completed in {baseline_duration:.1f}s")

    with open(out_dir / "baseline_0shot.md", "w", encoding="utf-8") as f:
        f.write(baseline_report)

    results["baseline_duration"] = round(baseline_duration, 1)
    results["baseline_word_count"] = len(baseline_report.split())

    # Step 3: Compare dimensions
    print("\n--- Step 3: Dimension comparison ---")
    ds_analysis = analyze_report(deepsynth_report) if deepsynth_report else {}
    bl_analysis = analyze_report(baseline_report)

    comparison = {
        "corpus_id": corpus_id,
        "corpus_label": info["label"],
        "text_length": len(text),
        "model": model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline": ds_analysis,
        "baseline_0shot": bl_analysis,
        "deltas": {},
    }

    # Compute deltas
    for dim in ["textual_citations", "word_count", "section_count"]:
        ds_val = ds_analysis.get(dim, 0)
        bl_val = bl_analysis.get(dim, 0)
        comparison["deltas"][dim] = {
            "pipeline": ds_val,
            "baseline": bl_val,
            "delta": ds_val - bl_val,
        }

    # Fallacy comparison
    ds_fallacies = ds_analysis.get("named_fallacies", [])
    bl_fallacies = bl_analysis.get("named_fallacies", [])
    comparison["deltas"]["named_fallacies"] = {
        "pipeline": len(ds_fallacies),
        "baseline": len(bl_fallacies),
        "delta": len(ds_fallacies) - len(bl_fallacies),
        "pipeline_detail": [f["name"] for f in ds_fallacies],
        "baseline_detail": [f["name"] for f in bl_fallacies],
    }

    # Formal methods
    ds_formal = ds_analysis.get("formal_method_findings", {})
    bl_formal = bl_analysis.get("formal_method_findings", {})
    comparison["deltas"]["formal_methods"] = {
        "pipeline": list(ds_formal.keys()),
        "baseline": list(bl_formal.keys()),
        "pipeline_unique": list(set(ds_formal.keys()) - set(bl_formal.keys())),
    }

    # Cross-text parallels
    comparison["deltas"]["cross_text_parallels"] = {
        "pipeline": ds_analysis.get("has_cross_text_parallels", False),
        "baseline": bl_analysis.get("has_cross_text_parallels", False),
    }

    # Convergence depth (substance: unfakeable by a 0-shot)
    ds_conv = ds_analysis.get("convergence", {})
    bl_conv = bl_analysis.get("convergence", {})
    comparison["deltas"]["convergence_depth"] = {
        "pipeline": ds_conv.get("verdict_count", 0),
        "baseline": bl_conv.get("verdict_count", 0),
        "delta": ds_conv.get("verdict_count", 0) - bl_conv.get("verdict_count", 0),
        "pipeline_max_convergence": ds_conv.get("max_convergence", 0),
    }

    # Computed artifacts (substance: concrete solver output, not name-dropping)
    ds_art = ds_analysis.get("computed_artifacts", {})
    bl_art = bl_analysis.get("computed_artifacts", {})
    comparison["deltas"]["computed_artifacts"] = {
        "pipeline": list(ds_art.keys()),
        "baseline": list(bl_art.keys()),
        "pipeline_unique": list(set(ds_art.keys()) - set(bl_art.keys())),
    }

    # Verdict — surface (vocabulary) + substance (computation) categories.
    # The substance categories are the ones a 0-shot structurally cannot win.
    pipeline_advantages = []
    if comparison["deltas"]["textual_citations"]["delta"] > 0:
        pipeline_advantages.append("more_textual_citations")
    if comparison["deltas"]["named_fallacies"]["delta"] > 0:
        pipeline_advantages.append("more_named_fallacies")
    if ds_formal and not bl_formal:
        pipeline_advantages.append("formal_methods_unique_to_pipeline")
    if (
        comparison["deltas"]["cross_text_parallels"]["pipeline"]
        and not comparison["deltas"]["cross_text_parallels"]["baseline"]
    ):
        pipeline_advantages.append("cross_text_parallels_unique")
    if comparison["deltas"]["convergence_depth"]["delta"] > 0:
        pipeline_advantages.append("convergence_depth_unique")
    if comparison["deltas"]["computed_artifacts"]["pipeline_unique"]:
        pipeline_advantages.append("computed_artifacts_unique")

    substance_categories = [
        c
        for c in pipeline_advantages
        if c in ("convergence_depth_unique", "computed_artifacts_unique")
    ]
    comparison["verdict"] = {
        "pipeline_advantage_categories": pipeline_advantages,
        "substance_advantage_categories": substance_categories,
        "meets_threshold": len(pipeline_advantages) >= 3,
        "meets_substance_threshold": len(substance_categories) >= 1,
    }

    # Save comparison
    with open(out_dir / "comparison.json", "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"\n--- Comparison Summary: {info['label']} ---")
    print(
        f"Pipeline report: {ds_analysis.get('word_count', 0)} words, {ds_analysis.get('section_count', 0)} sections"
    )
    print(
        f"Baseline report: {bl_analysis.get('word_count', 0)} words, {bl_analysis.get('section_count', 0)} sections"
    )
    print(
        f"Textual citations: pipeline={ds_analysis.get('textual_citations', 0)}, baseline={bl_analysis.get('textual_citations', 0)}"
    )
    print(
        f"Named fallacies: pipeline={len(ds_fallacies)}, baseline={len(bl_fallacies)}"
    )
    print(
        f"Formal methods: pipeline={list(ds_formal.keys())}, baseline={list(bl_formal.keys())}"
    )
    print(
        f"Cross-text parallels: pipeline={ds_analysis.get('has_cross_text_parallels', False)}, baseline={bl_analysis.get('has_cross_text_parallels', False)}"
    )
    print(
        f"Convergence verdicts: pipeline={ds_conv.get('verdict_count', 0)} (max {ds_conv.get('max_convergence', 0)} methods), baseline={bl_conv.get('verdict_count', 0)}"
    )
    print(
        f"Computed artifacts: pipeline={list(ds_art.keys())}, baseline={list(bl_art.keys())}"
    )
    print(f"Pipeline advantages: {pipeline_advantages}")
    print(f"  of which SUBSTANCE (unfakeable): {substance_categories}")
    print(f"Meets ≥3 categories threshold: {comparison['verdict']['meets_threshold']}")
    print(
        f"Meets substance threshold (≥1): {comparison['verdict']['meets_substance_threshold']}"
    )
    print(f"\nSaved to {out_dir}/")

    return comparison


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, help="Corpus ID (A, B, C) or 'all'")
    parser.add_argument(
        "--skip-pipeline",
        action="store_true",
        help="Skip pipeline run, use cached results",
    )
    args = parser.parse_args()

    corpora = ["A", "B", "C"] if args.corpus.lower() == "all" else [args.corpus.upper()]
    comparisons = []
    for cid in corpora:
        comp = await run_comparison(cid, skip_pipeline=args.skip_pipeline)
        comparisons.append(comp)

    # Global verdict
    if len(comparisons) > 1:
        print(f"\n{'='*60}")
        print("GLOBAL COMPARISON VERDICT")
        print(f"{'='*60}")
        for c in comparisons:
            label = c["corpus_label"]
            v = c["verdict"]
            icon = "PASS" if v["meets_threshold"] else "FAIL"
            sub = (
                "SUBSTANCE-WIN"
                if v.get("meets_substance_threshold")
                else "no-substance"
            )
            print(
                f"  [{icon}] [{sub}] {label}: {len(v['pipeline_advantage_categories'])} advantage categories — {v['pipeline_advantage_categories']}"
            )


if __name__ == "__main__":
    asyncio.run(main())
