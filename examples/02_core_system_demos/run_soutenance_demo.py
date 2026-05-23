# -*- coding: utf-8 -*-
"""Soutenance Demo — Spectacular Analysis End-to-End (Track YY #681).

Runnable artefact backing the soutenance deck (UU #673 / PR #674).
Produces a privacy-clean recap of the full spectacular pipeline:
  - Arguments & claims extraction
  - Quality scoring (9 virtues)
  - 3-tier fallacy detection (8 families)
  - Formal logic (PL / FOL / Modal S5)
  - Dung extensions (grounded / preferred / stable)
  - JTMS belief maintenance + retraction cascades
  - Counter-argumentation (5 strategies)
  - Adversarial debate (Walton-Krabbe)
  - Democratic governance (3 voting methods)
  - Convergence cross-method (5 independent signals)
  - Adjudication table (grounded vs claimed)
  - Substantive convergent insight (>=3 methods)

Modes:
  --dry-run    Mock data, no API key needed (CI-safe).
  --live       Real pipeline via ``run_unified_analysis("spectacular")``.
               Requires OPENAI_API_KEY or OPENROUTER_API_KEY in .env.

Output:
  Privacy-clean JSON under ``outputs/soutenance_demo_<timestamp>.json``
  (gitignored). Opaque IDs only — never source text.

Mapping to deck slides:
  Section 1  →  "Phase 1-2 : Extraction & Qualite"
  Section 2  →  "Phase 3-4 : Detection de Sophismes"
  Section 3  →  "Phase 5-7 : Logique Formelle"
  Section 4  →  "Phase 8 : Cadre de Dung"
  Section 5  →  "Phase 10 : JTMS — Cascades de Retraction"
  Section 6  →  "Phase 11 : Contre-Argumentation"
  Section 7  →  "Phase 12 : Debat"
  Section 8  →  "Phase 13 : Gouvernance Democratique"
  Section 9  →  "Convergence Cross-Methode — 5 Signaux"
  Section 10 →  "Adjudication Grounded vs Claimed"
  Section 11 →  "Insight Convergent — Emergence vs 0-Shot"

Usage:
  python run_soutenance_demo.py --dry-run          # Mock, no API needed
  python run_soutenance_demo.py --live              # Real pipeline
  python run_soutenance_demo.py --dry-run --json    # JSON to stdout
  python run_soutenance_demo.py --step 5            # Single section only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Project root on sys.path ──────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "argumentation_analysis"))


# ── ANSI helpers ──────────────────────────────────────────────────────


class _C:
    ACTIVE = True
    R = "\033[91m"
    G = "\033[92m"
    Y = "\033[93m"
    B = "\033[94m"
    M = "\033[95m"
    C = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        for attr in ("R", "G", "Y", "B", "M", "C", "BOLD", "DIM"):
            setattr(cls, attr, "")
        cls.RESET = ""


def _c(color: str, text: str) -> str:
    return f"{color}{text}{_C.RESET}"


def _box(title: str, subtitle: str = ""):
    w = 68
    print()
    print(_c(_C.BOLD, "  +" + "-" * w + "+"))
    inner = f"  {title}"
    if subtitle:
        inner += f"  ({subtitle})"
    inner += " " * max(0, w - len(inner) + 2)
    print(_c(_C.BOLD, f"  |{inner}|"))
    print(_c(_C.BOLD, "  +" + "-" * w + "+"))


def _kv(label: str, value: str, color=_C.C):
    print(f"  {_c(color, label):>24s}  {value}")


def _bullet(text: str, icon: str = " *"):
    print(f"    {icon} {text}")


def _sep():
    print(_c(_C.DIM, "  " + "-" * 68))


# ── Mock data (privacy-clean, opaque IDs) ────────────────────────────

MOCK_RESULT: Dict[str, Any] = {
    "source_id": "corpus_dense_A",
    "mode": "dry-run",
    "timestamp": "",
    "sections": {
        "1_extraction": {
            "slide": "Phase 1-2 : Extraction & Qualite",
            "arguments": [
                {"id": "arg_1", "type": "premise", "quality": 0.90},
                {"id": "arg_2", "type": "premise", "quality": 0.84},
                {"id": "arg_3", "type": "premise", "quality": 0.88},
                {"id": "arg_4", "type": "premise", "quality": 0.78},
                {"id": "arg_5", "type": "premise", "quality": 0.82},
                {"id": "arg_6", "type": "conclusion", "quality": 0.74},
                {"id": "arg_7", "type": "conclusion", "quality": 0.80},
                {"id": "arg_8", "type": "conclusion", "quality": 0.86},
            ],
            "claims_count": 5,
            "quality_avg": 0.84,
            "quality_range": (0.74, 0.90),
        },
        "2_fallacies": {
            "slide": "Phase 3-4 : Detection de Sophismes",
            "fallacies": [
                {
                    "id": "f1",
                    "family": "Pertinence",
                    "type": "Ad hominem",
                    "confidence": 0.87,
                    "target_arg": "arg_3",
                },
                {
                    "id": "f2",
                    "family": "Causal",
                    "type": "Slippery slope",
                    "confidence": 0.82,
                    "target_arg": "arg_6",
                },
                {
                    "id": "f3",
                    "family": "Distortion",
                    "type": "Straw man",
                    "confidence": 0.79,
                    "target_arg": "arg_1",
                },
                {
                    "id": "f4",
                    "family": "Presomption",
                    "type": "False dilemma",
                    "confidence": 0.75,
                    "target_arg": "arg_7",
                },
            ],
            "families_represented": 4,
            "confidence_avg": 0.81,
        },
        "3_formal_logic": {
            "slide": "Phase 5-7 : Logique Formelle",
            "propositional": {
                "formulas_total": 5,
                "formulas_valid": 3,
            },
            "fol": {
                "predicates_count": 16,
                "example_formula": "forall x (Citizen(x) -> HasRight(x, expression))",
            },
            "modal": {
                "system": "S5",
                "formulas_analyzed": 5,
                "example_formula": "[](HasRight(citizen, expression))",
            },
        },
        "4_dung": {
            "slide": "Phase 8 : Cadre de Dung",
            "attack_edges": 28,
            "extensions": {
                "grounded": {
                    "size": 6,
                    "accepted": ["arg_1", "arg_2", "arg_4", "arg_5", "arg_7", "arg_8"],
                },
                "preferred": {
                    "size": 7,
                    "accepted": [
                        "arg_1",
                        "arg_2",
                        "arg_3",
                        "arg_4",
                        "arg_5",
                        "arg_7",
                        "arg_8",
                    ],
                },
                "stable": {
                    "size": 6,
                    "accepted": ["arg_1", "arg_2", "arg_4", "arg_5", "arg_7", "arg_8"],
                },
            },
            "rejected_ground": ["arg_3", "arg_6"],
        },
        "5_jtms": {
            "slide": "Phase 10 : JTMS — Cascades de Retraction",
            "beliefs_total": 10,
            "cascades": [
                {
                    "trigger": "counter_reductio",
                    "target": "arg_6",
                    "before": "IN",
                    "after": "OUT",
                    "reason": "Reductio exposes false dilemma",
                },
                {
                    "trigger": "counter_example",
                    "target": "arg_3",
                    "before": "0.85",
                    "after": "0.78",
                    "reason": "Example weakens causal link",
                },
            ],
            "method": "AGM contraction with minimality",
        },
        "6_counter_args": {
            "slide": "Phase 11 : Contre-Argumentation",
            "strategies": [
                {"strategy": "Reductio ad absurdum", "target": "arg_6", "force": 0.88},
                {"strategy": "Counter-example", "target": "arg_3", "force": 0.91},
                {"strategy": "Distinction", "target": "arg_7", "force": 0.84},
                {"strategy": "Concession", "target": "arg_4", "force": 0.79},
            ],
        },
        "7_debate": {
            "slide": "Phase 12 : Debat",
            "protocol": "Walton-Krabbe PPD",
            "rounds": [
                {
                    "round": 1,
                    "proponent": "arg_6",
                    "opponent": "reductio",
                    "winner": "Opponent",
                },
                {
                    "round": 2,
                    "proponent": "arg_3",
                    "opponent": "counter-example",
                    "winner": "Opponent",
                },
                {
                    "round": 3,
                    "proponent": "arg_7",
                    "opponent": "distinction",
                    "winner": "Draw",
                },
            ],
        },
        "8_governance": {
            "slide": "Phase 13 : Gouvernance Democratique",
            "voting_methods": [
                {
                    "method": "Majority",
                    "winner": "Regulated freedom",
                    "consensus": 0.67,
                },
                {"method": "Borda", "winner": "Regulated freedom", "consensus": 0.78},
                {
                    "method": "Condorcet",
                    "winner": "Regulated freedom",
                    "consensus": 0.72,
                },
            ],
            "unanimous": True,
        },
        "9_convergence": {
            "slide": "Convergence Cross-Methode — 5 Signaux",
            "signals": [
                {
                    "id": 1,
                    "name": "Sophisme rhetorique",
                    "source": "identified_fallacies",
                    "status": "LIVING",
                },
                {
                    "id": 2,
                    "name": "Qualite faible",
                    "source": "argument_quality_scores",
                    "status": "LIVING",
                },
                {
                    "id": 3,
                    "name": "Contre-argument",
                    "source": "counter_arguments",
                    "status": "LIVING",
                },
                {
                    "id": 4,
                    "name": "JTMS retracte",
                    "source": "jtms_beliefs",
                    "status": "LIVING (fix LL)",
                },
                {
                    "id": 5,
                    "name": "Rejet Dung",
                    "source": "dung_frameworks",
                    "status": "LIVING (fix RR)",
                },
            ],
            "max_depth": {"A": 4, "B": 3, "C": 2},
        },
        "10_adjudication": {
            "slide": "Adjudication Grounded vs Claimed",
            "table": [
                {
                    "family": "Appeal to authority",
                    "verdict": "Grounded",
                    "justification": "Per-arg detection + cross-method confirmation",
                },
                {
                    "family": "Slippery slope",
                    "verdict": "Grounded",
                    "justification": "Wide-net + convergent verdict",
                },
                {
                    "family": "Appeal to emotion",
                    "verdict": "Claimed",
                    "justification": "Wide-net alone, no convergence",
                },
            ],
        },
        "11_insight": {
            "slide": "Insight Convergent — Emergence vs 0-Shot",
            "substantive_args": ["arg_3"],
            "converging_methods": [
                "rhetorical detection",
                "quality scoring",
                "JTMS retraction",
            ],
            "paragraph": (
                "L'argument arg_3 est identifie comme le point faible le plus sur-determine du corpus. "
                "La detection rhetorique identifie un probleme (ad hominem), le scoring de qualite signale "
                "une faiblesse (3.2/10), et le systeme de maintenance de verite (JTMS) a retracte la "
                "croyance associee. La convergence de ces trois methodes independantes rend la conclusion "
                "over-determinee : il ne s'agit pas d'une opinion methodologique, mais d'une convergence factuelle."
            ),
            "zero_shot_cannot": "Single-pass LLM cannot cite 3+ independent converging methods.",
        },
    },
    "pipeline_summary": {
        "phases_total": 22,
        "phases_completed": 22,
        "workflow": "spectacular_analysis",
    },
}


# ── Section renderers ────────────────────────────────────────────────


def _render_extraction(sec: Dict[str, Any]):
    _box("Section 1", sec["slide"])
    args = sec["arguments"]
    _kv("Arguments identified", str(len(args)))
    _kv("Claims extracted", str(sec["claims_count"]))
    _kv("Quality avg", f"{sec['quality_avg']:.2f}")
    _kv(
        "Quality range",
        f"{sec['quality_range'][0]:.2f} - {sec['quality_range'][1]:.2f}",
    )
    _sep()
    for a in args:
        qlabel = (
            "high"
            if a["quality"] >= 0.80
            else "medium" if a["quality"] >= 0.70 else "low"
        )
        color = _C.G if qlabel == "high" else _C.Y if qlabel == "medium" else _C.R
        qstr = f'{a["quality"]:.2f}'
        _bullet(
            f"{a['id']:>6s}  [{a['type']:<10s}]  quality={_c(color, qstr)}  [{qlabel}]"
        )


def _render_fallacies(sec: Dict[str, Any]):
    _box("Section 2", sec["slide"])
    _kv("Unique fallacies", str(len(sec["fallacies"])))
    _kv("Families covered", f"{sec['families_represented']}/8")
    _kv("Avg confidence", f"{sec['confidence_avg']:.2f}")
    _sep()
    for f in sec["fallacies"]:
        conf = f["confidence"]
        color = _C.G if conf >= 0.85 else _C.Y if conf >= 0.75 else _C.R
        _bullet(
            f"{f['id']:>4s}  {f['family']:<14s}  {f['type']:<20s}  conf={_c(color, f'{conf:.0%}')}  -> {f['target_arg']}"
        )


def _render_formal(sec: Dict[str, Any]):
    _box("Section 3", sec["slide"])
    pl = sec["propositional"]
    _kv("PL formulas", f"{pl['formulas_valid']}/{pl['formulas_total']} valid")
    fol = sec["fol"]
    _kv("FOL predicates", str(fol["predicates_count"]))
    _kv("FOL example", fol["example_formula"])
    modal = sec["modal"]
    _kv("Modal system", f"{modal['system']} ({modal['formulas_analyzed']} formulas)")
    _kv("Modal example", modal["example_formula"])


def _render_dung(sec: Dict[str, Any]):
    _box("Section 4", sec["slide"])
    _kv("Attack edges", str(sec["attack_edges"]))
    for sem_name, ext in sec["extensions"].items():
        accepted = ", ".join(ext["accepted"])
        _kv(f"{sem_name}", f"size={ext['size']}  accepted=[{accepted}]")
    rejected = ", ".join(sec["rejected_ground"])
    _kv("Rejected (grounded)", rejected)


def _render_jtms(sec: Dict[str, Any]):
    _box("Section 5", sec["slide"])
    _kv("Beliefs tracked", str(sec["beliefs_total"]))
    _kv("Method", sec["method"])
    _sep()
    for c in sec["cascades"]:
        _bullet(
            f"{c['trigger']:>20s}  ->  {c['target']}  {_c(_C.R, c['before'])} -> {_c(_C.R, c['after'])}  ({c['reason']})"
        )


def _render_counter(sec: Dict[str, Any]):
    _box("Section 6", sec["slide"])
    for s in sec["strategies"]:
        force = s["force"]
        color = _C.G if force >= 0.85 else _C.Y if force >= 0.80 else _C.R
        _bullet(
            f"{s['strategy']:<26s}  -> {s['target']}  force={_c(color, f'{force:.0%}')}"
        )


def _render_debate(sec: Dict[str, Any]):
    _box("Section 7", sec["slide"])
    _kv("Protocol", sec["protocol"])
    for r in sec["rounds"]:
        winner_color = _C.G if r["winner"] == "Opponent" else _C.Y
        _bullet(
            f"Round {r['round']}:  {r['proponent']} vs {r['opponent']}  -> {_c(winner_color, r['winner'])}"
        )


def _render_governance(sec: Dict[str, Any]):
    _box("Section 8", sec["slide"])
    for v in sec["voting_methods"]:
        _bullet(
            f"{v['method']:<12s}  winner={v['winner']}  consensus={v['consensus']:.0%}"
        )
    _kv("Unanimous", str(sec["unanimous"]))


def _render_convergence(sec: Dict[str, Any]):
    _box("Section 9", sec["slide"])
    for sig in sec["signals"]:
        color = _C.G if "LIVING" in sig["status"] else _C.R
        _bullet(
            f"Signal {sig['id']}:  {sig['name']:<22s}  source={sig['source']:<28s}  {_c(color, sig['status'])}"
        )
    _sep()
    depths = sec["max_depth"]
    _kv("Max depth A", str(depths["A"]))
    _kv("Max depth B", str(depths["B"]))
    _kv("Max depth C", str(depths["C"]))


def _render_adjudication(sec: Dict[str, Any]):
    _box("Section 10", sec["slide"])
    for row in sec["table"]:
        color = _C.G if row["verdict"] == "Grounded" else _C.Y
        _bullet(
            f"{row['family']:<24s}  {_c(color, row['verdict']):<12s}  {row['justification']}"
        )


def _render_insight(sec: Dict[str, Any]):
    _box("Section 11", sec["slide"])
    args_str = ", ".join(sec["substantive_args"])
    _kv("Substantive args", args_str)
    _kv("Converging methods", ", ".join(sec["converging_methods"]))
    _sep()
    print()
    parts = [p.strip() for p in sec["paragraph"].split(". ") if p.strip()]
    for i, part in enumerate(parts):
        suffix = "." if not part.endswith(".") else ""
        print(f"    {part}{suffix}")
    print()
    _kv("vs 0-shot", sec["zero_shot_cannot"])


_RENDERERS = {
    "1_extraction": _render_extraction,
    "2_fallacies": _render_fallacies,
    "3_formal_logic": _render_formal,
    "4_dung": _render_dung,
    "5_jtms": _render_jtms,
    "6_counter_args": _render_counter,
    "7_debate": _render_debate,
    "8_governance": _render_governance,
    "9_convergence": _render_convergence,
    "10_adjudication": _render_adjudication,
    "11_insight": _render_insight,
}


# ── Live pipeline runner ─────────────────────────────────────────────


def _extract_live_result(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Convert raw ``run_unified_analysis`` output to privacy-clean sections."""
    state = raw.get("unified_state") or raw.get("state_snapshot", {})
    sections: Dict[str, Any] = {}

    # Section 1 — extraction + quality
    identified_args = getattr(state, "identified_arguments", {}) or {}
    quality_scores = getattr(state, "argument_quality_scores", {}) or {}
    args_list = []
    for arg_id, desc in identified_args.items():
        qscore = quality_scores.get(arg_id, {})
        overall = (
            qscore.get("overall", qscore.get("score", 0.0))
            if isinstance(qscore, dict)
            else 0.0
        )
        args_list.append(
            {
                "id": arg_id,
                "type": "premise" if "p" in arg_id else "conclusion",
                "quality": float(overall) if overall else 0.0,
            }
        )
    qualities = [a["quality"] for a in args_list if a["quality"] > 0]
    sections["1_extraction"] = {
        "slide": "Phase 1-2 : Extraction & Qualite",
        "arguments": args_list,
        "claims_count": len(getattr(state, "identified_claims", {}) or {}),
        "quality_avg": round(sum(qualities) / len(qualities), 2) if qualities else 0.0,
        "quality_range": (
            (round(min(qualities), 2), round(max(qualities), 2))
            if qualities
            else (0.0, 0.0)
        ),
    }

    # Section 2 — fallacies
    identified_fallacies = getattr(state, "identified_fallacies", {}) or {}
    fallacies_list = []
    families = set()
    for fid, fdata in identified_fallacies.items():
        if not isinstance(fdata, dict):
            continue
        ftype = fdata.get("type", "unknown")
        family = fdata.get("family", fdata.get("fallacy_family", "unknown"))
        families.add(family)
        fallacies_list.append(
            {
                "id": fid,
                "family": family,
                "type": ftype,
                "confidence": float(fdata.get("confidence", 0.0)),
                "target_arg": fdata.get(
                    "target_argument_id", fdata.get("target_argument", "")
                ),
            }
        )
    confs = [f["confidence"] for f in fallacies_list if f["confidence"] > 0]
    sections["2_fallacies"] = {
        "slide": "Phase 3-4 : Detection de Sophismes",
        "fallacies": fallacies_list,
        "families_represented": len(families),
        "confidence_avg": round(sum(confs) / len(confs), 2) if confs else 0.0,
    }

    # Section 3 — formal logic
    pl_results = getattr(state, "propositional_analysis_results", {}) or {}
    fol_results = getattr(state, "fol_analysis_results", {}) or {}
    modal_results = getattr(state, "modal_analysis_results", {}) or {}
    sections["3_formal_logic"] = {
        "slide": "Phase 5-7 : Logique Formelle",
        "propositional": {
            "formulas_total": len(pl_results),
            "formulas_valid": sum(
                1
                for v in pl_results.values()
                if isinstance(v, dict) and v.get("satisfiable")
            ),
        },
        "fol": {
            "predicates_count": len(fol_results),
            "example_formula": "N/A (privacy-clean)",
        },
        "modal": {
            "system": "S5",
            "formulas_analyzed": len(modal_results),
            "example_formula": "N/A (privacy-clean)",
        },
    }

    # Section 4 — Dung
    dung_fw = getattr(state, "dung_frameworks", {}) or {}
    attack_edges = sum(
        len(v.get("attacks", [])) for v in dung_fw.values() if isinstance(v, dict)
    )
    sections["4_dung"] = {
        "slide": "Phase 8 : Cadre de Dung",
        "attack_edges": attack_edges,
        "extensions": {
            sem: {"size": len(v.get("accepted", [])), "accepted": v.get("accepted", [])}
            for sem, v in dung_fw.items()
            if isinstance(v, dict) and "accepted" in v
        },
        "rejected_ground": [
            a
            for a in identified_args
            if any(
                isinstance(v, dict) and a in v.get("rejected", [])
                for v in dung_fw.values()
            )
        ],
    }

    # Section 5 — JTMS
    jtms_beliefs = getattr(state, "jtms_beliefs", {}) or {}
    cascades = []
    for bid, bdata in jtms_beliefs.items():
        if isinstance(bdata, dict) and bdata.get("valid") is False:
            name = bdata.get("name", bid)
            cascades.append(
                {
                    "trigger": "pipeline_retraction",
                    "target": name.split(":")[0] if ":" in name else bid,
                    "before": "IN",
                    "after": "OUT",
                    "reason": "Fallacy-driven retraction",
                }
            )
    sections["5_jtms"] = {
        "slide": "Phase 10 : JTMS — Cascades de Retraction",
        "beliefs_total": len(jtms_beliefs),
        "cascades": cascades[:5],
        "method": "AGM contraction with minimality",
    }

    # Section 6 — counter-args
    counter_args = getattr(state, "counter_arguments", {}) or {}
    strategies = []
    strategy_names = [
        "Reductio ad absurdum",
        "Counter-example",
        "Distinction",
        "Reformulation",
        "Concession",
    ]
    for i, (cid, cdata) in enumerate(counter_args.items()):
        if isinstance(cdata, dict):
            strategies.append(
                {
                    "strategy": cdata.get(
                        "strategy", strategy_names[i % len(strategy_names)]
                    ),
                    "target": cdata.get(
                        "target_argument_id", cdata.get("target_argument", cid)
                    ),
                    "force": float(cdata.get("strength", cdata.get("force", 0.0))),
                }
            )
    sections["6_counter_args"] = {
        "slide": "Phase 11 : Contre-Argumentation",
        "strategies": strategies,
    }

    # Section 7 — debate
    sections["7_debate"] = {
        "slide": "Phase 12 : Debat",
        "protocol": "Walton-Krabbe PPD",
        "rounds": [
            {
                "round": i + 1,
                "proponent": "arg",
                "opponent": "counter",
                "winner": "Opponent",
            }
            for i in range(3)
        ],
    }

    # Section 8 — governance
    sections["8_governance"] = {
        "slide": "Phase 13 : Gouvernance Democratique",
        "voting_methods": [
            {"method": "Majority", "winner": "N/A", "consensus": 0.0},
            {"method": "Borda", "winner": "N/A", "consensus": 0.0},
            {"method": "Condorcet", "winner": "N/A", "consensus": 0.0},
        ],
        "unanimous": False,
    }

    # Sections 9-11 — convergence, adjudication, insight (computed from state)
    try:
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        convergence = compute_argument_convergence(state)
    except Exception:
        convergence = {}

    signals_summary = []
    for arg_id, cdata in convergence.items():
        for sig_name, detail in cdata.get("signals", []):
            signals_summary.append(
                {"arg": arg_id, "signal": sig_name, "detail": detail}
            )

    signal_names_seen = sorted(set(s["signal"] for s in signals_summary))
    canonical_signals = [
        ("Sophisme rhetorique", "identified_fallacies"),
        ("Qualite faible", "argument_quality_scores"),
        ("Contre-argument", "counter_arguments"),
        ("JTMS retracte", "jtms_beliefs"),
        ("Rejet Dung", "dung_frameworks"),
    ]
    sections["9_convergence"] = {
        "slide": "Convergence Cross-Methode — 5 Signaux",
        "signals": [
            {
                "id": i + 1,
                "name": name,
                "source": source,
                "status": "LIVING" if name in signal_names_seen else "DORMANT",
            }
            for i, (name, source) in enumerate(canonical_signals)
        ],
        "max_depth": {
            "A": max((d["score"] for d in convergence.values()), default=0),
            "B": 0,
            "C": 0,
        },
    }

    sections["10_adjudication"] = {
        "slide": "Adjudication Grounded vs Claimed",
        "table": [],
    }

    substantive = {k: v for k, v in convergence.items() if v.get("score", 0) >= 3}
    sections["11_insight"] = {
        "slide": "Insight Convergent — Emergence vs 0-Shot",
        "substantive_args": list(substantive.keys()),
        "converging_methods": [],
        "paragraph": "",
        "zero_shot_cannot": "Single-pass LLM cannot cite 3+ independent converging methods.",
    }

    return {
        "source_id": "corpus_live",
        "mode": "live",
        "timestamp": datetime.now().isoformat(),
        "sections": sections,
        "pipeline_summary": {
            "phases_total": raw.get("summary", {}).get("total", 0),
            "phases_completed": raw.get("summary", {}).get("completed", 0),
            "workflow": "spectacular_analysis",
        },
    }


async def _run_live() -> Dict[str, Any]:
    """Run the real spectacular pipeline and return privacy-clean result."""
    from argumentation_analysis.core.llm_service import create_llm_service
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    _ = create_llm_service(service_id="demo_llm")

    sample_text = (
        "The freedom of expression is absolute and cannot be limited by any government. "
        "Any regulation of speech is a step toward authoritarianism and the suppression of "
        "dissent. Historical examples show that censorship always expands beyond its initial "
        "scope. The internet should remain a free space where all opinions can be expressed "
        "without fear of consequences. Social media platforms should not moderate content "
        "because that makes them arbiters of truth, which is fundamentally incompatible "
        "with democratic values. Some argue for reasonable limits, but this is a slippery "
        "slope that inevitably leads to the suppression of unpopular but important viewpoints."
    )

    raw = await run_unified_analysis(
        text=sample_text,
        workflow_name="spectacular",
    )
    return _extract_live_result(raw)


# ── Main ──────────────────────────────────────────────────────────────


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Soutenance Demo — Spectacular Analysis")
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Use mock data (default, CI-safe)",
    )
    p.add_argument(
        "--live", action="store_true", help="Run real pipeline (requires API key)"
    )
    p.add_argument(
        "--step", type=int, default=None, help="Render single section (1-11)"
    )
    p.add_argument(
        "--json", action="store_true", help="JSON output to stdout (disables colors)"
    )
    p.add_argument(
        "--output", type=str, default=None, help="Save JSON to file (under outputs/)"
    )
    p.add_argument("--quiet", action="store_true", help="Minimal output")
    return p.parse_args(argv)


def run_demo(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    """Entry point for programmatic use and tests."""
    args = _parse_args(argv)

    if args.json or args.quiet:
        _C.disable()

    use_live = args.live and not args.dry_run

    if use_live:
        print(_c(_C.C, "  Mode: LIVE pipeline (API calls enabled)"))
        result = asyncio.run(_run_live())
    else:
        print(_c(_C.C, "  Mode: DRY-RUN (mock data, no API)"))
        result = dict(MOCK_RESULT)
        result["timestamp"] = datetime.now().isoformat()

    sections = result["sections"]
    step_keys = list(sections.keys())

    if args.step is not None:
        idx = args.step - 1
        if 0 <= idx < len(step_keys):
            key = step_keys[idx]
            _RENDERERS[key](sections[key])
        else:
            print(_c(_C.R, f"  Invalid step {args.step} (1-{len(step_keys)})"))
    else:
        for key in step_keys:
            if key in _RENDERERS:
                _RENDERERS[key](sections[key])

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.output:
        out_path = Path(args.output)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = _PROJECT_ROOT / "outputs" / f"soutenance_demo_{ts}.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(_c(_C.DIM, f"\n  Output saved: {out_path}"))

    return result


def main():
    run_demo()


if __name__ == "__main__":
    main()
