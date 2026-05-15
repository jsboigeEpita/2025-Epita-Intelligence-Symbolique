"""SCDA Sprint 1 Audit — conversational mode deep analysis on dense corpora.

Runs the conversational orchestrator (PM + specialists) on 3 dense texts,
saves full transcripts + state, scores specialists, generates audit report.

Usage:
    python scripts/scda_audit.py --corpus A [--max-turns 10]
    python scripts/scda_audit.py --corpus all

Outputs: outputs/scda_audit/<opaque_id>/ (gitignored)
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

# Load .env into environment (API keys + passphrase)
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
    "A": {"src_idx": 11, "label": "corpus_dense_A", "desc": "Trump UN GA 2025 (~58K EN)"},
    "B": {"src_idx": 3, "label": "corpus_dense_B", "desc": "Hitler collection (~50K DE extract)"},
    "C": {"src_idx": 2, "label": "corpus_dense_C", "desc": "Kremlin 21/02/2022 (~46K EN)"},
}

OUTPUTS_DIR = Path("outputs/scda_audit")


def load_corpus(corpus_id: str) -> str:
    """Load text for a given corpus. For B (Hitler), extract ~50K coherent segment."""
    info = CORPORA[corpus_id]
    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    defs = load_extract_definitions(
        Path("argumentation_analysis/data/extract_sources.json.gz.enc"), key
    )
    src = defs[info["src_idx"]]
    text = src.get("full_text", "")

    if corpus_id == "B":
        # src3 = 3M chars collection. Extract a coherent ~50K segment.
        # The collection has dated speeches. Find a substantial single speech.
        # Look for date markers like "1939.01.30" or similar patterns
        # and extract a contiguous ~50K block.

        # Strategy: find speech boundaries and pick the longest coherent block
        # that's close to 50K chars.
        speech_markers = re.split(r'(?=\d{4}\.\d{2}\.\d{2})', text)

        best_chunk = ""
        for chunk in speech_markers:
            if 30000 <= len(chunk) <= 60000:
                if len(chunk) > len(best_chunk):
                    best_chunk = chunk

        # If no single speech in range, take a ~50K slice from middle
        if not best_chunk:
            # Find a good starting point (speech boundary)
            start = len(text) // 4  # Start at 25% into the collection
            # Adjust to nearest speech boundary
            boundary = text.find("\n\n", start)
            if boundary > 0:
                start = boundary
            best_chunk = text[start:start + 50000]

        text = best_chunk
        print(f"  Extracted {len(text):,} chars from src3 (Hitler collection)")

    return text


def score_specialists(conversation_log: list[dict]) -> dict[str, dict]:
    """Score each specialist's contribution quality.

    Levels:
    - MUTE: Agent spoke 0 times or only empty messages
    - PARAPHRASING: Agent only restated input text without analysis
    - CITED_INSIGHT: Agent provided analysis with text citations
    - SINGULAR_INSIGHT: Agent produced unique insight no 0-shot LLM would make
    """
    agent_messages = {}
    for entry in conversation_log:
        agent = entry.get("agent", "unknown")
        content = entry.get("content", "")
        if not content or len(content.strip()) < 20:
            continue
        if agent not in agent_messages:
            agent_messages[agent] = []
        agent_messages[agent].append(content)

    scores = {}
    for agent, messages in agent_messages.items():
        total_chars = sum(len(m) for m in messages)
        total_msgs = len(messages)

        if total_msgs == 0 or total_chars < 50:
            level = "MUTE"
            evidence = "No substantive messages"
        elif total_chars < 200:
            level = "PARAPHRASING"
            evidence = f"Short contributions ({total_chars} chars total)"
        else:
            # Check for analytical depth markers
            all_text = " ".join(messages).lower()
            has_citations = bool(re.search(r'["\'][^"\']{20,}["\']', " ".join(messages)))
            has_formal = any(kw in all_text for kw in [
                "belief", "dung", "extension", "attack", "support",
                "formal", "logic", "propositional", "fol", "modal",
                "fallacy", "sophism", "ad hominem", "straw man",
                "tweety", "jtms", "retraction", "aspic",
                "counter-argument", "rebuttal", "ranking",
                "inconsistency", "contradiction",
            ])
            has_structure = any(kw in all_text for kw in [
                "firstly", "moreover", "however", "conclusion",
                "therefore", "analysis shows", "evidence suggests",
                "in contrast", "furthermore", "specifically",
            ])

            if has_formal and has_citations:
                level = "SINGULAR_INSIGHT"
                evidence = f"Formal method usage + citations ({total_chars} chars)"
            elif has_citations or has_formal:
                level = "CITED_INSIGHT"
                evidence = f"{'Formal methods' if has_formal else 'Citations'} ({total_chars} chars)"
            else:
                level = "PARAPHRASING"
                evidence = f"No formal/citation depth ({total_chars} chars)"

        scores[agent] = {
            "level": level,
            "messages": total_msgs,
            "total_chars": total_chars,
            "evidence": evidence,
        }

    return scores


async def run_audit(corpus_id: str, max_turns: int = 10) -> dict[str, Any]:
    """Run conversational analysis on a corpus and save results."""
    info = CORPORA[corpus_id]
    print(f"\n{'='*60}")
    print(f"SCDA Audit — {info['label']} ({info['desc']})")
    print(f"{'='*60}")

    # Load text
    text = load_corpus(corpus_id)
    print(f"Loaded {len(text):,} chars")

    # Run conversational analysis
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        run_conversational_analysis,
    )

    start = time.time()
    print(f"Starting conversational analysis (max_turns_per_phase={max_turns})...")
    result = await run_conversational_analysis(
        text=text,
        max_turns_per_phase=max_turns,
        spectacular=True,
    )
    duration = time.time() - start
    print(f"Analysis completed in {duration:.1f}s")

    # Extract results
    conversation_log = result.get("conversation_log", [])
    state = result.get("unified_state", None)
    state_snapshot = result.get("state_snapshot", {})
    trace_report = result.get("trace_report", {})

    # Score specialists
    specialist_scores = score_specialists(conversation_log)

    # Save outputs
    out_dir = OUTPUTS_DIR / info["label"]
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save conversation log
    with open(out_dir / "conversation_log.json", "w", encoding="utf-8") as f:
        json.dump(conversation_log, f, indent=2, ensure_ascii=False, default=str)

    # Save state snapshot
    if state:
        snap = state.get_state_snapshot(summarize=False) if hasattr(state, 'get_state_snapshot') else state_snapshot
        with open(out_dir / "state_snapshot.json", "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=2, ensure_ascii=False, default=str)

        # Save enrichment summary
        enrichment = state.get_enrichment_summary() if hasattr(state, 'get_enrichment_summary') else {}
        with open(out_dir / "enrichment_summary.json", "w", encoding="utf-8") as f:
            json.dump(enrichment, f, indent=2, ensure_ascii=False, default=str)

    # Save trace report
    with open(out_dir / "trace_report.json", "w", encoding="utf-8") as f:
        json.dump(trace_report, f, indent=2, ensure_ascii=False, default=str)

    # Save audit summary
    audit = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "corpus_id": corpus_id,
        "corpus_label": info["label"],
        "text_length": len(text),
        "duration_seconds": round(duration, 1),
        "max_turns_per_phase": max_turns,
        "conversation_turns": len(conversation_log),
        "specialist_scores": specialist_scores,
        "final_conclusion": getattr(state, 'final_conclusion', None) if state else None,
    }
    with open(out_dir / "audit_summary.json", "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False, default=str)

    # Print summary
    print(f"\n--- Audit Summary: {info['label']} ---")
    print(f"Duration: {duration:.1f}s | Turns: {len(conversation_log)}")
    print(f"\nSpecialist Scores:")
    for agent, score in sorted(specialist_scores.items(), key=lambda x: x[1]["total_chars"], reverse=True):
        icon = {"MUTE": ".", "PARAPHRASING": "~", "CITED_INSIGHT": "+", "SINGULAR_INSIGHT": "★"}[score["level"]]
        print(f"  {icon} {agent}: {score['level']} ({score['messages']} msgs, {score['total_chars']} chars)")

    print(f"\nSaved to {out_dir}/")
    return audit


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True,
                        help="Corpus ID (A, B, C) or 'all'")
    parser.add_argument("--max-turns", type=int, default=10,
                        help="Max turns per phase (default: 10)")
    args = parser.parse_args()

    corpora = ["A", "B", "C"] if args.corpus.lower() == "all" else [args.corpus.upper()]
    audits = []
    for cid in corpora:
        audit = await run_audit(cid, max_turns=args.max_turns)
        audits.append(audit)

    # Print global summary
    if len(audits) > 1:
        print(f"\n{'='*60}")
        print("GLOBAL SCDA AUDIT SUMMARY")
        print(f"{'='*60}")
        for a in audits:
            print(f"\n{a['corpus_label']} ({a['text_length']:,} chars, {a['duration_seconds']}s):")
            for agent, score in a["specialist_scores"].items():
                icon = {"MUTE": ".", "PARAPHRASING": "~", "CITED_INSIGHT": "+", "SINGULAR_INSIGHT": "★"}[score["level"]]
                print(f"  {icon} {agent}: {score['level']}")


if __name__ == "__main__":
    asyncio.run(main())
