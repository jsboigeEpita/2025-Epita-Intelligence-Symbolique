# -*- coding: utf-8 -*-
"""
Demonstration EPITA — Parcours Spectacular v3.0

Escalated pedagogical journey through all system capabilities.
Dual target: students (pedagogical) + soutenance (impressive).

6 steps in increasing complexity:
  1. Extraction & Claims    — raw text → structured facts
  2. Formal Logic           — NL → FOL/Modal/Propositional
  3. Fallacy Detection      — 8-family taxonomy drill-down
  4. Argumentation Frameworks — Dung extensions + JTMS beliefs
  5. Adversarial Debate     — multi-agent counter-arguments
  6. Synthesis              — unified narrative with all signals

Usage:
  python demonstration_epita_spectacular.py              # Full demo
  python demonstration_epita_spectacular.py --step 3     # Run single step
  python demonstration_epita_spectacular.py --json       # JSON output (no colors)
  python demonstration_epita_spectacular.py --quiet      # Minimal output
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# ── Console formatting ──────────────────────────────────────────────

class C:
    """ANSI color codes — disabled when --json or --quiet."""
    ACTIVE = True
    R = "\033[91m"   # red
    G = "\033[92m"   # green
    Y = "\033[93m"   # yellow
    B = "\033[94m"   # blue
    M = "\033[95m"   # magenta
    C = "\033[96m"   # cyan
    W = "\033[97m"   # white
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        for attr in ("R", "G", "Y", "B", "M", "C", "W", "BOLD", "DIM"):
            setattr(cls, attr, "")
        cls.RESET = ""


def _c(color: str, text: str) -> str:
    return f"{color}{text}{C.RESET}"


def box(title: str, subtitle: str = ""):
    w = 72
    print()
    print(_c(C.C, "╔" + "═" * w + "╗"))
    print(_c(C.C, "║") + _c(C.BOLD, f"  {title:^{w-4}}") + _c(C.C, "║"))
    if subtitle:
        print(_c(C.C, "║") + _c(C.DIM, f"  {subtitle:^{w-4}}") + _c(C.C, "║"))
    print(_c(C.C, "╚" + "═" * w + "╗" if not subtitle else "╚" + "═" * w + "╝"))
    print()


def section_header(step_num: int, total: int, title: str, icon: str):
    w = 70
    progress = f"Step {step_num}/{total}"
    print()
    print(_c(C.B, "┌" + "─" * w + "┐"))
    print(_c(C.B, "│") + f"  {icon}  {_c(C.BOLD, title)}" + " " * max(0, w - 6 - len(title) - len(progress)) + _c(C.DIM, progress) + _c(C.B, " │"))
    print(_c(C.B, "└" + "─" * w + "┘"))


def kv(label: str, value: str, label_color=C.C):
    print(f"  {_c(label_color, label):>20s}  {value}")


def bullet(text: str, icon: str = "•"):
    print(f"    {icon} {text}")


def badge(text: str, color=C.G):
    return _c(color, f"[{text}]")


def separator():
    print(_c(C.DIM, "  " + "─" * 68))


# ── Mock spectacular pipeline outputs ───────────────────────────────
# These simulate what the spectacular workflow (issue #347) would produce.
# When the real pipeline is available, replace MOCK_RUN_STEP with real calls.

MOCK_SOURCE = (
    "Le réchauffement climatique est un mythe inventé par les médias. "
    "97% des scientifiques seraient d'accord, mais la science n'est pas une démocratie ! "
    "Si nous arrêtons le charbon demain, l'économie s'effondrera et des millions de gens "
    "perdront leur emploi. D'ailleurs, cet hiver a été le plus froid depuis 10 ans, "
    "ce qui prouve que la planète ne se réchauffe pas. Les énergies renouvelables "
    "sont une arnaque financée par George Soros pour contrôler le marché de l'énergie."
)

MOCK_SPECTACULAR_RESULT = {
    "source_id": "doc_A",
    "source_title": "Climate skepticism discourse (opaque ID)",
    "timestamp": datetime.now().isoformat(),
    "steps": {
        "1_extraction": {
            "title": "Extraction & Claims",
            "icon": "🔬",
            "narration": (
                "The pipeline first isolates verifiable claims from the raw discourse. "
                "Each claim is scored for factual grounding potential."
            ),
            "output": {
                "extracted_claims": [
                    {"id": "c1", "text": "Global warming is a myth invented by media", "type": "factual_claim", "confidence": 0.92},
                    {"id": "c2", "text": "97% of scientists agree", "type": "statistical_reference", "confidence": 0.88},
                    {"id": "c3", "text": "Stopping coal will collapse the economy", "type": "causal_prediction", "confidence": 0.75},
                    {"id": "c4", "text": "This winter was the coldest in 10 years", "type": "empirical_observation", "confidence": 0.95},
                    {"id": "c5", "text": "Renewables are a scam funded by Soros", "type": "conspiracy_theory", "confidence": 0.97},
                ],
                "extracted_arguments": [
                    {"id": "a1", "premises": ["c4"], "conclusion": "c1", "type": "empirical_counter"},
                    {"id": "a2", "premises": ["c3"], "conclusion": "oppose_transition", "type": "slippery_slope"},
                ],
                "extraction_stats": {"claims": 5, "arguments": 2, "time_ms": 340},
            },
        },
        "2_formal_logic": {
            "title": "Formal Logic Translation",
            "icon": "📐",
            "narration": (
                "Natural language claims are translated into formal representations — "
                "FOL, propositional, and modal logic — enabling automated reasoning."
            ),
            "output": {
                "fol_formulas": [
                    {"id": "f1", "natural": "Stopping coal will collapse economy", "formal": "∀x (StopCoal(x) → Collapse(Economy))", "valid": False},
                    {"id": "f2", "natural": "Cold winter disproves warming", "formal": "ColdWinter ∧ ¬GlobalWarming", "valid": False},
                    {"id": "f3", "natural": "97% scientists agree", "formal": "∃S (|{s ∈ Scientists : Believes(s, Warming)}| / |Scientists| ≥ 0.97)", "valid": True},
                ],
                "propositional": [
                    {"formula": "¬(ColdWinter → ¬GlobalWarming)", "satisfiable": True, "tautology": False},
                    {"formula": "(StopCoal → Collapse) ∨ ¬(StopCoal → Collapse)", "satisfiable": True, "tautology": True},
                ],
                "modal": [
                    {"formula": "◇(EconomyCollapse)", "system": "S5", "meaning": "Economy collapse is possible (not necessary)"},
                ],
                "validation_summary": {"total": 6, "valid": 2, "invalid": 3, "tautology": 1},
            },
        },
        "3_fallacy_detection": {
            "title": "Fallacy Taxonomy Detection",
            "icon": "🔍",
            "narration": (
                "A 3-tier hybrid detector (neural + symbolic + rule-based) classifies "
                "fallacies into 8 families with severity and confidence scores."
            ),
            "output": {
                "detected_fallacies": [
                    {"type": "Ad Hominem", "sub": "Circumstantial", "target": "c5", "confidence": 0.91, "severity": "high",
                     "excerpt": "arnaque financée par George Soros", "explanation": "Attacks motives instead of addressing renewable energy arguments"},
                    {"type": "Straw Man", "sub": "Misrepresentation", "target": "c1", "confidence": 0.85, "severity": "high",
                     "excerpt": "mythe inventé par les médias", "explanation": "Oversimplifies scientific consensus as media invention"},
                    {"type": "Slippery Slope", "sub": "Causal Chain", "target": "c3", "confidence": 0.88, "severity": "medium",
                     "excerpt": "économie s'effondrera et des millions perdront leur emploi", "explanation": "Unwarranted extrapolation from coal stoppage to economic collapse"},
                    {"type": "Hasty Generalization", "sub": "Small Sample", "target": "c4", "confidence": 0.82, "severity": "medium",
                     "excerpt": "cet hiver a été le plus froid", "explanation": "Single winter ≠ climate trend (weather vs climate confusion)"},
                    {"type": "Appeal to Authority", "sub": "False Authority", "target": "c2", "confidence": 0.73, "severity": "low",
                     "excerpt": "la science n'est pas une démocratie", "explanation": "Dismisses consensus by false analogy with democracy"},
                    {"type": "Red Herring", "sub": "Distraction", "target": "c5", "confidence": 0.79, "severity": "medium",
                     "excerpt": "George Soros pour contrôler le marché", "explanation": "Conspiracy theory diverts from energy policy discussion"},
                ],
                "family_counts": {"Ad Hominem": 1, "Straw Man": 1, "Slippery Slope": 1, "Hasty Generalization": 1,
                                  "Appeal to Authority": 1, "Red Herring": 1, "False Dilemma": 0, "Circular Reasoning": 0},
                "severity_summary": {"high": 2, "medium": 3, "low": 1},
                "confidence_avg": 0.83,
            },
        },
        "4_argumentation_frameworks": {
            "title": "Argumentation Frameworks (Dung + JTMS)",
            "icon": "🕸️",
            "narration": (
                "Dung's abstract argumentation computes which arguments are collectively acceptable. "
                "Simultaneously, a JTMS tracks belief propagation with retraction cascades."
            ),
            "output": {
                "dung": {
                    "arguments": {"A1": "Claim: Warming is a myth", "A2": "Counter: 97% consensus",
                                  "A3": "Claim: Cold winter disproves warming", "A4": "Counter: Weather ≠ climate",
                                  "A5": "Claim: Renewables are scam", "A6": "Counter: Cost curves show viability"},
                    "attacks": [
                        {"from": "A2", "to": "A1", "type": "direct"},
                        {"from": "A4", "to": "A3", "type": "undercut"},
                        {"from": "A6", "to": "A5", "type": "direct"},
                        {"from": "A1", "to": "A2", "type": "rebuttal"},
                    ],
                    "extensions": {
                        "grounded": ["A2", "A4", "A6"],
                        "preferred": [["A1", "A3", "A5"], ["A2", "A4", "A6"]],
                        "stable": [["A2", "A4", "A6"]],
                    },
                    "analysis": "Grounded extension favors counter-arguments — skepticism claims are not defensible without additional support.",
                },
                "jtms": {
                    "beliefs": {
                        "b_warming_real": {"status": "IN", "confidence": 0.95, "source": "scientific_consensus"},
                        "b_media_myth": {"status": "OUT", "confidence": 0.0, "retracted_by": "b_warming_real"},
                        "b_cold_winter": {"status": "IN", "confidence": 0.9, "source": "empirical_observation"},
                        "b_disprove_warming": {"status": "OUT", "confidence": 0.0, "retracted_by": "b_weather_not_climate"},
                        "b_weather_not_climate": {"status": "IN", "confidence": 0.97, "source": "epistemic_knowledge"},
                        "b_coal_stop_collapse": {"status": "UNDECIDED", "confidence": 0.5, "source": "unsupported_causal"},
                    },
                    "retraction_cascade": [
                        "b_warming_real → b_media_myth (retracted)",
                        "b_weather_not_climate → b_disprove_warming (retracted)",
                    ],
                    "summary": {"in": 3, "out": 2, "undecided": 1},
                },
            },
        },
        "5_adversarial_debate": {
            "title": "Multi-Agent Adversarial Debate",
            "icon": "⚔️",
            "narration": (
                "Two agents debate: one defends the original discourse, the other attacks it. "
                "A governance module votes on the final position using 7 voting methods."
            ),
            "output": {
                "rounds": [
                    {"round": 1, "defender": "The 97% consensus reference shows scientific backing",
                     "attacker": "Consensus is not proof — the text itself calls it 'not a democracy'",
                     "score_defender": 0.4, "score_attacker": 0.7},
                    {"round": 2, "defender": "Coal shutdown risks are real economic concerns",
                     "attacker": "Slippery slope — no evidence of total collapse",
                     "score_defender": 0.3, "score_attacker": 0.8},
                    {"round": 3, "defender": "Cold winter data is empirical evidence",
                     "attacker": "Weather ≠ climate — single data point fallacy",
                     "score_defender": 0.2, "score_attacker": 0.9},
                ],
                "counter_arguments": [
                    {"strategy": "reductio_ad_absurdum", "text": "If cold winter disproves warming, does a hot summer prove it?",
                     "strength": 0.88},
                    {"strategy": "counter_example", "text": "Germany phased out coal without economic collapse",
                     "strength": 0.82},
                    {"strategy": "distinction", "text": "Distinguish weather events from climate trends (30+ year averages)",
                     "strength": 0.91},
                ],
                "governance": {
                    "methods": {
                        "majority": "reject_original",
                        "borda": "reject_original",
                        "condorcet": "reject_original",
                        "approval": "reject_original",
                    },
                    "consensus": "reject_original",
                    "consensus_strength": 0.87,
                },
                "debate_winner": "attacker",
                "final_score": {"defender": 0.30, "attacker": 0.80},
            },
        },
        "6_synthesis": {
            "title": "Unified Narrative Synthesis",
            "icon": "📊",
            "narration": (
                "All signals converge into a single spectacular analysis: "
                "32 fields across 13 dimensions, ready for human decision-making."
            ),
            "output": {
                "overall_assessment": "REJECTED — 6 fallacies detected, 0/5 claims survive formal validation, grounded extension favors counter-arguments",
                "quality_score": {
                    "clarity": 0.65, "coherence": 0.40, "relevance": 0.70,
                    "evidence": 0.15, "logic": 0.20, "completeness": 0.35,
                    "overall": 0.41,
                },
                "fallacy_density": "6 fallacies / 5 claims = 1.2 fallacies per claim (critical)",
                "strongest_counter": "Weather ≠ climate distinction (strength 0.91)",
                "recommendation": "This discourse uses 6 rhetorical fallacies to construct a denial narrative. No claim survives formal logic validation. The Dung grounded extension rejects all original arguments. Recommended action: fact-check and provide counter-evidence for each claim.",
                "field_count": 32,
                "dimensions": [
                    "claims_extraction", "formal_logic", "fallacy_detection",
                    "dung_framework", "jtms_beliefs", "counter_arguments",
                    "debate_transcript", "governance_vote", "quality_scores",
                    "retraction_cascade", "adversarial_score", "synthesis_narrative",
                    "recommendation",
                ],
            },
        },
    },
}


# ── Step renderers ───────────────────────────────────────────────────

def render_step_1(data: Dict):
    """Extraction & Claims."""
    out = data["output"]
    section_header(1, 6, out.get("title", "Extraction & Claims"), "🔬")
    print()
    kv("Source:", MOCK_SOURCE[:90] + "...", C.DIM)
    print()
    kv("Claims extracted:", str(len(out["extracted_claims"])), C.G)
    for claim in out["extracted_claims"]:
        conf_color = C.G if claim["confidence"] >= 0.85 else C.Y if claim["confidence"] >= 0.70 else C.R
        print(f"    {_c(conf_color, f'{claim["confidence"]:.0%}')}  {claim["text"][:65]}")
        print(f"         {_c(C.DIM, f'type={claim["type"]}  id={claim["id"]}')}")

    print()
    kv("Arguments:", str(len(out["extracted_arguments"])), C.B)
    for arg in out["extracted_arguments"]:
        premises = ", ".join(arg["premises"])
        print(f"    {premises} → {arg['conclusion']}  {_c(C.DIM, f'({arg["type"]})')}")

    print()
    kv("Extraction time:", f"{out['extraction_stats']['time_ms']}ms", C.DIM)


def render_step_2(data: Dict):
    """Formal Logic."""
    out = data["output"]
    section_header(2, 6, out.get("title", "Formal Logic"), "📐")
    print()

    kv("FOL Translations:", str(len(out["fol_formulas"])), C.M)
    for f in out["fol_formulas"]:
        valid_icon = badge("VALID", C.G) if f["valid"] else badge("INVALID", C.R)
        print(f"    {valid_icon}  {f['formal'][:55]}")
        print(f"         {_c(C.DIM, f'≈ {f["natural"][:55]}')}")

    print()
    kv("Propositional:", str(len(out["propositional"])), C.B)
    for p in out["propositional"]:
        tags = []
        if p["satisfiable"]:
            tags.append(badge("SAT", C.G))
        if p["tautology"]:
            tags.append(badge("TAUT", C.C))
        print(f"    {' '.join(tags)}  {p['formula'][:55]}")

    print()
    kv("Modal:", str(len(out["modal"])) + " formula(s)", C.Y)
    for m in out["modal"]:
        print(f"    {m['formula']}  {_c(C.DIM, f'({m['system']}: {m['meaning'][:45]})')}")

    vs = out["validation_summary"]
    print()
    kv("Validation:", f"{vs['valid']} valid, {vs['invalid']} invalid, {vs['tautology']} tautology", C.C)


def render_step_3(data: Dict):
    """Fallacy Detection."""
    out = data["output"]
    section_header(3, 6, out.get("title", "Fallacy Detection"), "🔍")
    print()

    sev_colors = {"high": C.R, "medium": C.Y, "low": C.G}
    for fallacy in out["detected_fallacies"]:
        sc = sev_colors.get(fallacy["severity"], C.W)
        print(f"    {_c(sc, f'[{fallacy["severity"].upper():>6s}]')}  {_c(C.BOLD, fallacy['type'])} → {fallacy['sub']}")
        print(f"           {fallacy['excerpt'][:60]}")
        print(f"           {_c(C.DIM, fallacy['explanation'][:65])}")
        print()

    kv("Families:", ", ".join(f"{k}({v})" for k, v in out["family_counts"].items() if v > 0), C.C)
    ss = out["severity_summary"]
    kv("Severity:", f"{ss['high']} high / {ss['medium']} medium / {ss['low']} low", C.Y)
    kv("Avg confidence:", f"{out['confidence_avg']:.0%}", C.G)


def render_step_4(data: Dict):
    """Dung + JTMS."""
    out = data["output"]
    section_header(4, 6, out.get("title", "Argumentation Frameworks"), "🕸️")
    print()

    dung = out["dung"]
    kv("Dung Arguments:", str(len(dung["arguments"])), C.B)
    for aid, content in dung["arguments"].items():
        print(f"    {aid}: {content}")

    print()
    kv("Attacks:", str(len(dung["attacks"])), C.R)
    for atk in dung["attacks"]:
        print(f"    {atk['from']} → {atk['to']}  {_c(C.DIM, f'({atk["type"]})')}")

    print()
    ext = dung["extensions"]
    kv("Grounded:", ", ".join(ext["grounded"]), C.G)
    kv("Preferred:", str(len(ext["preferred"])) + " extension(s)", C.Y)
    for i, pref in enumerate(ext["preferred"]):
        print(f"         {{{', '.join(pref)}}}")
    kv("Stable:", ", ".join(ext["stable"][0]) if ext["stable"] else "none", C.C)

    print()
    kv("Analysis:", dung["analysis"][:65], C.DIM)

    print()
    separator()
    print()

    jtms = out["jtms"]
    kv("JTMS Beliefs:", str(len(jtms["beliefs"])), C.M)
    status_colors = {"IN": C.G, "OUT": C.R, "UNDECIDED": C.Y}
    for bid, bdata in jtms["beliefs"].items():
        sc = status_colors.get(bdata["status"], C.W)
        extra = ""
        if "retracted_by" in bdata:
            extra = f"  ← {_c(C.R, f'retracted by {bdata['retracted_by']}')}"
        print(f"    {_c(sc, f'{bdata["status"]:>10s}')}  {bid}{extra}")

    print()
    if jtms["retraction_cascade"]:
        kv("Retraction cascade:", "", C.R)
        for step in jtms["retraction_cascade"]:
            print(f"      {step}")

    s = jtms["summary"]
    print()
    kv("JTMS Summary:", f"{s['in']} IN / {s['out']} OUT / {s['undecided']} UNDECIDED", C.C)


def render_step_5(data: Dict):
    """Adversarial Debate."""
    out = data["output"]
    section_header(5, 6, out.get("title", "Adversarial Debate"), "⚔️")
    print()

    for r in out["rounds"]:
        print(f"    {_c(C.BOLD, f'Round {r["round"]}')}")
        print(f"      {_c(C.B, 'Defender:')}  {r['defender'][:60]}")
        print(f"      {_c(C.R, 'Attacker:')}  {r['attacker'][:60]}")
        print(f"             {_c(C.B, f'D {r['score_defender']:.1f}')}  vs  {_c(C.R, f'A {r['score_attacker']:.1f}')}")
        print()

    kv("Counter-arguments:", str(len(out["counter_arguments"])), C.G)
    for ca in out["counter_arguments"]:
        print(f"    {badge(ca['strategy'], C.M)}  {ca['text'][:55]}")
        print(f"         {_c(C.DIM, f'strength={ca['strength']:.0%}')}")

    gov = out["governance"]
    print()
    kv("Governance:", f"consensus={gov['consensus']} ({gov['consensus_strength']:.0%})", C.Y)
    for method, result in gov["methods"].items():
        icon = badge("✓", C.G) if result == "reject_original" else badge("?", C.Y)
        print(f"    {icon}  {method}: {result}")

    print()
    winner = out["debate_winner"]
    scores = out["final_score"]
    kv("Winner:", _c(C.G if winner == "attacker" else C.R, f"{winner.upper()}"), C.BOLD)
    kv("Final score:", f"defender {scores['defender']:.2f} vs attacker {scores['attacker']:.2f}", C.C)


def render_step_6(data: Dict):
    """Synthesis."""
    out = data["output"]
    section_header(6, 6, out.get("title", "Unified Synthesis"), "📊")
    print()

    kv("Assessment:", _c(C.R, out["overall_assessment"][:65]), C.BOLD)
    print()

    qs = out["quality_score"]
    kv("Quality — Overall:", f"{qs['overall']:.0%}", C.R if qs["overall"] < 0.5 else C.Y)
    for dim in ("clarity", "coherence", "relevance", "evidence", "logic", "completeness"):
        val = qs[dim]
        color = C.G if val >= 0.7 else C.Y if val >= 0.5 else C.R
        bar_len = int(val * 20)
        bar = _c(color, "█" * bar_len) + _c(C.DIM, "░" * (20 - bar_len))
        print(f"    {dim:>13s}  {bar} {_c(color, f'{val:.0%}')}")

    print()
    kv("Fallacy density:", out["fallacy_density"], C.R)
    kv("Strongest counter:", out["strongest_counter"], C.G)
    print()
    kv("Recommendation:", out["recommendation"][:65], C.C)
    print()
    kv("Fields rendered:", str(out["field_count"]), C.G)
    kv("Dimensions:", str(len(out["dimensions"])), C.C)


# ── Main runner ──────────────────────────────────────────────────────

STEP_RENDERERS = {
    "1_extraction": render_step_1,
    "2_formal_logic": render_step_2,
    "3_fallacy_detection": render_step_3,
    "4_argumentation_frameworks": render_step_4,
    "5_adversarial_debate": render_step_5,
    "6_synthesis": render_step_6,
}

STEP_KEYS = list(STEP_RENDERERS.keys())


def run_demo(step_filter: Optional[int] = None, json_output: bool = False, quiet: bool = False):
    """Run the spectacular demonstration."""
    if json_output or quiet:
        C.disable()

    start = time.time()

    if json_output:
        if step_filter:
            key = STEP_KEYS[step_filter - 1]
            print(json.dumps(MOCK_SPECTACULAR_RESULT["steps"][key], indent=2, ensure_ascii=False))
        else:
            print(json.dumps(MOCK_SPECTACULAR_RESULT, indent=2, ensure_ascii=False))
        return MOCK_SPECTACULAR_RESULT

    if not quiet:
        box(
            "EPITA — SPECTACULAR RHETORICAL ANALYSIS",
            "Parcours pédagogique v3.0 · 6 capabilities · 1 document",
        )
        print(f"  {_c(C.DIM, 'Source:')} {_c(C.C, MOCK_SPECTACULAR_RESULT['source_id'])} — {MOCK_SPECTACULAR_RESULT['source_title']}")
        print(f"  {_c(C.DIM, 'Time:')}   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        separator()

    steps_to_run = STEP_KEYS
    if step_filter:
        if step_filter < 1 or step_filter > len(STEP_KEYS):
            print(_c(C.R, f"Invalid step {step_filter}. Must be 1-{len(STEP_KEYS)}."))
            return None
        steps_to_run = [STEP_KEYS[step_filter - 1]]

    for key in steps_to_run:
        step_data = MOCK_SPECTACULAR_RESULT["steps"][key]
        narration = step_data.get("narration", "")
        if narration:
            print(f"\n  {_c(C.DIM, '💡 ' + narration)}")
        STEP_RENDERERS[key](step_data)

    elapsed = time.time() - start

    if not quiet:
        print()
        box("DEMONSTRATION COMPLETE", f"6 steps · {elapsed:.2f}s · {MOCK_SPECTACULAR_RESULT['steps']['6_synthesis']['output']['field_count']} fields rendered")

    return MOCK_SPECTACULAR_RESULT


def parse_args():
    parser = argparse.ArgumentParser(
        description="EPITA Spectacular Rhetorical Analysis — Pedagogical Demo v3.0",
    )
    parser.add_argument("--step", type=int, choices=range(1, 7), help="Run a single step (1-6)")
    parser.add_argument("--json", action="store_true", help="JSON output (no colors/formatting)")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    return parser.parse_args()


def main():
    args = parse_args()
    result = run_demo(step_filter=args.step, json_output=args.json, quiet=args.quiet)
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
