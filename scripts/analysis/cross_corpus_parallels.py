#!/usr/bin/env python3
"""
Cross-Corpus Rhetorical Parallels Analysis — Track L (#603).

Loads all 3 corpus state snapshots from scda_audit outputs, extracts
structured metrics, and produces comparison data for the master report.

Outputs:
  - Console summary tables
  - JSON data for downstream report generation
  - CSV tables for fallacy frequency, cascade depth, and signatures

Usage:
    python scripts/analysis/cross_corpus_parallels.py [--output-dir OUTPUT_DIR]
"""

import json
import argparse
import csv
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

CORPORA = ["A", "B", "C"]
CORPUS_LABELS = {
    "A": "corpus_dense_A",
    "B": "corpus_dense_B",
    "C": "corpus_dense_C",
}

# Approximate token counts (from audit_summary text_length / 4)
TOKEN_ESTIMATES = {
    "A": 14513,
    "B": 14773,
    "C": 11598,
}

TEXT_LENGTHS = {
    "A": 58052,
    "B": 59092,
    "C": 46391,
}


def load_corpus_data(base_dir: Path, corpus_id: str) -> dict:
    """Load state_snapshot, audit_summary, and trace_report for a corpus."""
    label = CORPUS_LABELS[corpus_id]
    corpus_dir = base_dir / label

    state_path = corpus_dir / "state_snapshot.json"
    audit_path = corpus_dir / "audit_summary.json"
    trace_path = corpus_dir / "trace_report.json"

    data = {}

    if state_path.exists():
        with open(state_path, encoding="utf-8") as f:
            data["state"] = json.load(f)
    else:
        print(f"WARNING: {state_path} not found", file=sys.stderr)
        data["state"] = {}

    if audit_path.exists():
        with open(audit_path, encoding="utf-8") as f:
            data["audit"] = json.load(f)
    else:
        print(f"WARNING: {audit_path} not found", file=sys.stderr)
        data["audit"] = {}

    if trace_path.exists():
        with open(trace_path, encoding="utf-8") as f:
            data["trace"] = json.load(f)
    else:
        print(f"WARNING: {trace_path} not found", file=sys.stderr)
        data["trace"] = {}

    return data


def extract_quantitative_metrics(data: dict, corpus_id: str) -> dict:
    """Extract core quantitative metrics from state snapshot."""
    state = data.get("state", {})
    audit = data.get("audit", {})

    metrics = {
        "corpus_id": corpus_id,
        "text_length": TEXT_LENGTHS.get(corpus_id, 0),
        "token_estimate": TOKEN_ESTIMATES.get(corpus_id, 0),
        "duration_seconds": audit.get("duration_seconds", 0),
        "conversation_turns": audit.get("conversation_turns", 0),
        "identified_arguments": len(state.get("identified_arguments", {})),
        "identified_fallacies": len(state.get("identified_fallacies", {})),
        "counter_arguments": len(state.get("counter_arguments", [])),
        "jtms_beliefs": len(state.get("jtms_beliefs", {})),
        "dung_frameworks": len(state.get("dung_frameworks", {})),
        "aspic_results": len(state.get("aspic_results", {})),
        "belief_revision": len(state.get("belief_revision_results", {})),
        "nl_to_logic": len(state.get("nl_to_logic_translations", {})),
        "fol_analysis": len(state.get("fol_analysis_results", {})),
        "propositional_analysis": len(state.get("propositional_analysis_results", {})),
        "modal_analysis": len(state.get("modal_analysis_results", {})),
        "quality_scores": len(state.get("argument_quality_scores", {})),
        "governance_decisions": len(state.get("governance_decisions", {})),
        "debate_transcripts": len(state.get("debate_transcripts", {})),
    }

    # Normalize per 1000 tokens
    tokens = metrics["token_estimate"]
    if tokens > 0:
        metrics["arguments_per_1k"] = round(metrics["identified_arguments"] / tokens * 1000, 2)
        metrics["fallacies_per_1k"] = round(metrics["identified_fallacies"] / tokens * 1000, 2)
        metrics["counters_per_1k"] = round(metrics["counter_arguments"] / tokens * 1000, 2)
    else:
        metrics["arguments_per_1k"] = 0
        metrics["fallacies_per_1k"] = 0
        metrics["counters_per_1k"] = 0

    return metrics


def extract_fallacy_families(data: dict) -> Counter:
    """Extract fallacy types and count occurrences."""
    state = data.get("state", {})
    fallacies = state.get("identified_fallacies", {})
    family_counts = Counter()
    for fid, fdata in fallacies.items():
        ftype = fdata.get("type", "unknown")
        family_counts[normalize_fallacy_type(ftype)] += 1
    return family_counts


def normalize_fallacy_type(ftype: str) -> str:
    """Normalize fallacy type names to canonical families (EN canonical names).

    Handles mixed FR/EN types, parenthetical annotations, and slash variants.
    Strategy: try multiple keys derived from the raw type string.
    """
    mapping = {
        "post_hoc_ergo_propter_hoc": "Post hoc ergo propter hoc",
        "conspiracy_theory": "Conspiracy theory",
        "cherry_picking": "Cherry picking",
        "hasty_generalization": "Hasty generalization",
        "statistique_trompeuse": "Misleading statistics",
        "appel_a_la_pitie": "Appeal to pity",
        "poisoning_the_well": "Poisoning the well",
        "generalisation_abusive": "Hasty generalization",
        "victim_blaming": "Victim blaming",
        "appel_a_la_peur": "Appeal to fear",
        "faux_dilemme": "False dilemma",
        "sophisme_genetique": "Genetic fallacy",
        "homogeneisation": "Hasty generalization",
        "appel_a_l_appartenance": "Appeal to belonging",
        "simplicite_causale": "Causal oversimplification",
        "deux_torts_font_un_droit": "Two wrongs make a right",
        "cause_unique": "Single cause",
        "none": "Unclassified",
    }

    # Try the full normalized key first
    raw = ftype.lower().strip()
    # Remove parenthetical annotations like "(argumentum ad metum)"
    # and slash variants like "FR / EN" — keep first term
    cleaned = raw.split("/")[0].split("(")[0].strip()
    key = cleaned.replace(" ", "_").replace("'", "").replace("’", "")
    key = key.replace("-", "_").replace("’", "")

    result = mapping.get(key)
    if result:
        return result

    # Fallback: try the raw key with minimal cleanup
    key2 = raw.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_").replace("'", "").replace("-", "_")
    key2 = key2.replace("’", "")
    result = mapping.get(key2)
    if result:
        return result

    # Final fallback: try substring matching for compound labels
    for map_key, map_val in mapping.items():
        if map_key in key2 or map_key in key:
            return map_val

    return ftype


def extract_cascade_depth(data: dict) -> dict:
    """Extract cascade depth metrics (JTMS retractions, Dung cardinality, etc.)."""
    state = data.get("state", {})

    cascade = {}

    # JTMS retraction chain
    retraction_chain = state.get("jtms_retraction_chain", [])
    cascade["jtms_retraction_count"] = len(retraction_chain)
    cascade["jtms_retracted_args"] = [
        r.get("argument_id", r.get("belief_name", "unknown"))
        for r in retraction_chain
    ] if retraction_chain else []

    # JTMS beliefs detail
    jtms = state.get("jtms_beliefs", {})
    cascade["jtms_belief_count"] = len(jtms)
    cascade["jtms_belief_names"] = list(jtms.keys())

    # Dung framework detail
    dung = state.get("dung_frameworks", {})
    cascade["dung_count"] = len(dung)
    if dung:
        first_dung = list(dung.values())[0]
        cascade["dung_arg_count"] = first_dung.get("argument_count", len(first_dung.get("arguments", [])))
        cascade["dung_attack_count"] = first_dung.get("attack_count", len(first_dung.get("attacks", [])))
        cascade["dung_grounded_size"] = len(first_dung.get("grounded_extension", []))
    else:
        cascade["dung_arg_count"] = 0
        cascade["dung_attack_count"] = 0
        cascade["dung_grounded_size"] = 0

    # ASPIC detail
    aspic = state.get("aspic_results", {})
    cascade["aspic_count"] = len(aspic) if isinstance(aspic, (list, dict)) else 0
    if aspic:
        if isinstance(aspic, list):
            first_aspic = aspic[0] if aspic else {}
        elif isinstance(aspic, dict):
            first_aspic = list(aspic.values())[0]
        else:
            first_aspic = {}
        if isinstance(first_aspic, dict):
            cascade["aspic_total_args"] = first_aspic.get("total_arguments", 0)
            cascade["aspic_surviving"] = first_aspic.get("surviving_arguments", 0)
            cascade["aspic_defeated"] = first_aspic.get("defeated_arguments", 0)
        else:
            cascade["aspic_total_args"] = 1
            cascade["aspic_surviving"] = 0
            cascade["aspic_defeated"] = 0
    else:
        cascade["aspic_total_args"] = 0
        cascade["aspic_surviving"] = 0
        cascade["aspic_defeated"] = 0

    # Belief revision
    br = state.get("belief_revision_results", {})
    cascade["belief_revision_count"] = len(br)

    # NL-to-logic
    nl = state.get("nl_to_logic_translations", {})
    cascade["nl_to_logic_count"] = len(nl)

    return cascade


def extract_formal_method_signature(data: dict) -> dict:
    """Extract which formal methods activated for radar plot."""
    state = data.get("state", {})

    signature = {
        "argument_extraction": 1 if state.get("identified_arguments") else 0,
        "fallacy_detection": 1 if state.get("identified_fallacies") else 0,
        "counter_argument": 1 if state.get("counter_arguments") else 0,
        "jtms": 1 if state.get("jtms_beliefs") else 0,
        "dung": 1 if state.get("dung_frameworks") else 0,
        "aspic": 1 if state.get("aspic_results") else 0,
        "belief_revision": 1 if state.get("belief_revision_results") else 0,
        "nl_to_logic": 1 if state.get("nl_to_logic_translations") else 0,
        "fol": 1 if state.get("fol_analysis_results") else 0,
        "propositional": 1 if state.get("propositional_analysis_results") else 0,
        "modal": 1 if state.get("modal_analysis_results") else 0,
        "governance": 1 if state.get("governance_decisions") else 0,
        "debate": 1 if state.get("debate_transcripts") else 0,
    }

    # Cardinality per method
    signature["argument_count"] = len(state.get("identified_arguments", {}))
    signature["fallacy_count"] = len(state.get("identified_fallacies", {}))
    signature["counter_count"] = len(state.get("counter_arguments", []))
    signature["jtms_count"] = len(state.get("jtms_beliefs", {}))

    return signature


def extract_agent_activity(data: dict) -> dict:
    """Extract agent participation from audit_summary."""
    audit = data.get("audit", {})
    scores = audit.get("specialist_scores", {})

    agents = {}
    for agent_name, agent_data in scores.items():
        agents[agent_name] = {
            "level": agent_data.get("level", "unknown"),
            "messages": agent_data.get("messages", 0),
            "total_chars": agent_data.get("total_chars", 0),
        }

    return agents


def print_comparison_table(metrics_list: list):
    """Print a formatted comparison table."""
    print("\n" + "=" * 80)
    print("CROSS-CORPUS COMPARISON TABLE")
    print("=" * 80)

    fields = [
        ("text_length", "Text Length (chars)"),
        ("token_estimate", "Tokens (est.)"),
        ("duration_seconds", "Duration (s)"),
        ("conversation_turns", "Turns"),
        ("identified_arguments", "Arguments"),
        ("identified_fallacies", "Fallacies"),
        ("counter_arguments", "Counter-args"),
        ("jtms_beliefs", "JTMS Beliefs"),
        ("dung_frameworks", "Dung Frameworks"),
        ("aspic_results", "ASPIC Results"),
        ("belief_revision", "Belief Revision"),
        ("nl_to_logic", "NL-to-Logic"),
        ("fol_analysis", "FOL Analysis"),
        ("quality_scores", "Quality Scores"),
        ("arguments_per_1k", "Args / 1K tokens"),
        ("fallacies_per_1k", "Fallacies / 1K tokens"),
    ]

    header = f"{'Metric':<30}"
    for m in metrics_list:
        header += f"{'A' if m['corpus_id'] == 'A' else 'B' if m['corpus_id'] == 'B' else 'C':>10}"
    print(header)
    print("-" * 80)

    for key, label in fields:
        row = f"{label:<30}"
        for m in metrics_list:
            val = m.get(key, 0)
            if isinstance(val, float):
                row += f"{val:>10.2f}"
            else:
                row += f"{val:>10}"
        print(row)


def print_fallacy_family_table(families_by_corpus: dict, metrics_list: list):
    """Print normalized fallacy family comparison."""
    print("\n" + "=" * 80)
    print("FALLACY FAMILY FREQUENCY (normalized per 1K tokens)")
    print("=" * 80)

    all_families = sorted(set(
        fam for fams in families_by_corpus.values() for fam in fams
    ))

    tokens = {m["corpus_id"]: m["token_estimate"] for m in metrics_list}

    header = f"{'Family':<35}"
    for cid in CORPORA:
        header += f"{'A' if cid == 'A' else 'B' if cid == 'B' else 'C':>10}"
    header += f"{'Total':>10}"
    print(header)
    print("-" * 80)

    for family in all_families:
        row = f"{family:<35}"
        total = 0
        for cid in CORPORA:
            count = families_by_corpus[cid].get(family, 0)
            t = tokens.get(cid, 1)
            normalized = round(count / t * 1000, 2) if t > 0 else 0
            row += f"{normalized:>10.2f}"
            total += count
        row += f"{total:>10}"
        print(row)

    # Totals
    row = f"{'TOTAL':<35}"
    for cid in CORPORA:
        total = sum(families_by_corpus[cid].values())
        t = tokens.get(cid, 1)
        normalized = round(total / t * 1000, 2) if t > 0 else 0
        row += f"{normalized:>10.2f}"
    grand = sum(sum(f.values()) for f in families_by_corpus.values())
    row += f"{grand:>10}"
    print(row)


def save_json(data: dict, path: Path):
    """Save data as formatted JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {path}")


def save_csv(rows: list, headers: list, path: Path):
    """Save data as CSV."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Saved: {path}")


def main():
    parser = argparse.ArgumentParser(description="Cross-corpus parallels analysis (Track L #603)")
    parser.add_argument(
        "--base-dir",
        type=str,
        default="outputs/scda_audit",
        help="Base directory containing corpus_dense_A/B/C subdirectories",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="docs/reports/cross_corpus_data",
        help="Output directory for JSON/CSV data files",
    )
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    if not base_dir.is_absolute():
        base_dir = Path(__file__).resolve().parent.parent.parent / base_dir

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = Path(__file__).resolve().parent.parent.parent / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load all corpora
    print("Loading corpus data...")
    corpora_data = {}
    for cid in CORPORA:
        corpora_data[cid] = load_corpus_data(base_dir, cid)

    # Extract metrics
    metrics_list = []
    for cid in CORPORA:
        metrics = extract_quantitative_metrics(corpora_data[cid], cid)
        metrics_list.append(metrics)

    print_comparison_table(metrics_list)

    # Fallacy families
    families_by_corpus = {}
    for cid in CORPORA:
        families_by_corpus[cid] = extract_fallacy_families(corpora_data[cid])

    print_fallacy_family_table(families_by_corpus, metrics_list)

    # Cascade depth
    print("\n" + "=" * 80)
    print("CASCADE DEPTH ANALYSIS")
    print("=" * 80)
    cascade_data = {}
    for cid in CORPORA:
        cascade = extract_cascade_depth(corpora_data[cid])
        cascade_data[cid] = cascade
        print(f"\nCorpus {cid}:")
        for k, v in cascade.items():
            print(f"  {k}: {v}")

    # Formal method signatures (for radar plot)
    print("\n" + "=" * 80)
    print("FORMAL METHOD SIGNATURES (radar plot data)")
    print("=" * 80)
    signature_data = {}
    for cid in CORPORA:
        sig = extract_formal_method_signature(corpora_data[cid])
        signature_data[cid] = sig
        active = [k for k, v in sig.items() if v == 1 and k.endswith("_count") is False and k != "argument_count" and k != "fallacy_count" and k != "counter_count" and k != "jtms_count"]
        print(f"Corpus {cid}: {len(active)} active methods — {active}")

    # Agent activity
    print("\n" + "=" * 80)
    print("AGENT PARTICIPATION")
    print("=" * 80)
    agent_data = {}
    for cid in CORPORA:
        agents = extract_agent_activity(corpora_data[cid])
        agent_data[cid] = agents
        print(f"\nCorpus {cid}:")
        for name, info in agents.items():
            print(f"  {name}: {info['level']} ({info['messages']} msgs, {info['total_chars']} chars)")

    # Save outputs
    print("\n" + "=" * 80)
    print("SAVING OUTPUT FILES")
    print("=" * 80)

    # 1. Full metrics JSON
    save_json({
        "metrics": {m["corpus_id"]: m for m in metrics_list},
        "fallacy_families": {cid: dict(families_by_corpus[cid]) for cid in CORPORA},
        "cascade_depth": cascade_data,
        "formal_signatures": signature_data,
        "agent_activity": agent_data,
    }, output_dir / "cross_corpus_comparison.json")

    # 2. Fallacy frequency CSV
    all_families = sorted(set(
        fam for fams in families_by_corpus.values() for fam in fams
    ))
    rows = []
    for family in all_families:
        row = {"family": family}
        for cid in CORPORA:
            count = families_by_corpus[cid].get(family, 0)
            t = metrics_list[[m["corpus_id"] for m in metrics_list].index(cid)]["token_estimate"]
            row[f"{cid}_count"] = count
            row[f"{cid}_per_1k"] = round(count / t * 1000, 4) if t > 0 else 0
        rows.append(row)

    headers = ["family"] + [f"{cid}_{s}" for cid in CORPORA for s in ["count", "per_1k"]]
    save_csv(rows, headers, output_dir / "fallacy_frequency.csv")

    # 3. Cascade depth CSV
    cascade_rows = []
    for cid in CORPORA:
        row = {"corpus": cid}
        row.update(cascade_data[cid])
        cascade_rows.append(row)
    save_csv(cascade_rows, ["corpus"] + list(cascade_data["A"].keys()), output_dir / "cascade_depth.csv")

    # 4. Radar plot data CSV
    radar_rows = []
    for method in sorted(signature_data["A"].keys()):
        row = {"method": method}
        for cid in CORPORA:
            row[cid] = signature_data[cid].get(method, 0)
        radar_rows.append(row)
    save_csv(radar_rows, ["method"] + CORPORA, output_dir / "radar_signature.csv")

    print("\nDone. Output directory:", output_dir)


if __name__ == "__main__":
    main()
