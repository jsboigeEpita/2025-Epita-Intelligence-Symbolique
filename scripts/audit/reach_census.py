"""Offline, aggregate-only census of student contributions (#3549).

Only the JTMS counterfactual projection is measured; other projectors remain
unvalidated and are explicitly reported as not measured.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (  # noqa: E402
    build_act3_evidence,
    build_act3_prompt,
)

# Fields and vocabulary are observational proxies, not proof of attribution.
PROJECTS = {
    "1.4.1-JTMS": (
        ("jtms_retraction_chain", "jtms_beliefs", "atms_contexts"),
        r"r[ée]tractation|\bjtms\b|\batms\b",
    ),
    "1_2_7_argumentation_dialogique": (("debate_transcripts",), r"d[ée]bat|dialogue"),
    "2.1.6_multiagent_governance_prototype": (
        ("governance_decisions",),
        r"gouvernance|coalition|manipulab",
    ),
    "2.3.2-detection-sophismes": (("identified_fallacies",), r"sophisme|fallac"),
    "2.3.3-generation-contre-argument": (
        ("counter_arguments",),
        r"contre.argument|r[ée]futation",
    ),
    "2.3.5_argument_quality": (("argument_quality_scores",), r"qualit[ée]|vertu"),
    "2.3.6_local_llm": (("local_llm_results",), r"mod[èe]le local|llm local"),
    "3.1.5_Interface_Mobile": None,
    "abs_arg_dung": (("dung_frameworks",), r"\bdung\b|extension argumentative"),
    "Arg_Semantic_Index": (
        ("semantic_priority_spans", "semantic_index_refs"),
        r"index s[ée]mantique",
    ),
    "speech-to-text": None,
    "CaseAI": None,
}
ACTS = ("act1_framing", "act2_narrative", "act3_conclusion", "narrative_synthesis")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle-dir", type=Path, required=True)
    args = parser.parse_args()
    paths = sorted((args.cycle_dir / "states").glob("state_full_*.json"))
    if not paths:
        parser.error("no state files found")
    states = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    cycle = json.loads((args.cycle_dir / "cycle.json").read_text(encoding="utf-8"))
    print(
        "# reach census (partial: only JTMS counterfactual prompt projection measured)"
    )
    projected = 0
    for state in states:
        evidence = build_act3_evidence(SimpleNamespace(**state))
        prompt = build_act3_prompt(evidence)
        projected += any(
            finding.capability == "belief_maintenance"
            and bool(finding.statement)
            and finding.statement in prompt
            for finding in evidence.structured_findings
        )
    print("# command: python scripts/audit/reach_census.py --cycle-dir <cycle-dir>")
    print(
        f"# cycle head: {cycle.get('head', 'unknown')}; date: {datetime.date.today().isoformat()}"
    )
    print("| project | fields filled | Act III prompt | named in acts | regex |")
    print("|---|---|---|---|---|")
    for project, spec in PROJECTS.items():
        if spec is None:
            label = "not ported" if project == "CaseAI" else "n/a (channel)"
            print(f"| {project} | {label} | {label} | {label} | — |")
            continue
        fields, pattern = spec
        filled = sum(any(state.get(field) for field in fields) for state in states)
        named = sum(
            bool(
                re.search(
                    pattern, " ".join(str(state.get(act) or "") for act in ACTS), re.I
                )
            )
            for state in states
        )
        # Markdown tables split on pipes even inside inline code.
        display_pattern = pattern.replace("|", r"\|")
        prompt_count = (
            f"{projected} of {len(states)} (JTMS counterfactual only)"
            if project == "1.4.1-JTMS"
            else "not measured"
        )
        print(
            f"| {project} | {filled} of {len(states)} | {prompt_count} | {named} of {len(states)} | `{display_pattern}` |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
