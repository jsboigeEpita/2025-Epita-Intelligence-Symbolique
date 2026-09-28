"""Compare lexical taxonomy matches with a Git baseline, without exporting corpus text.

Usage: python scripts/compare_taxonomy_name_2812.py --baseline 96f0ced08
The encrypted corpus is decrypted only in memory; stdout contains aggregates.
"""

import argparse
import os
import subprocess
import sys
import types
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
SOURCE = "argumentation_analysis/agents/core/informal/taxonomy_sophism_detector.py"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="96f0ced08")
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    load_dotenv(ROOT / ".env")

    from argumentation_analysis.agents.core.informal.taxonomy_sophism_detector import (
        TaxonomySophismDetector,
    )
    from argumentation_analysis.core.io_manager import load_extract_definitions
    from argumentation_analysis.core.utils.crypto_utils import derive_encryption_key

    baseline_source = subprocess.check_output(
        ["git", "show", f"{args.baseline}:{SOURCE}"], cwd=ROOT, text=True
    )
    module = types.ModuleType(
        "argumentation_analysis.agents.core.informal._taxonomy_baseline_2812"
    )
    module.__package__ = "argumentation_analysis.agents.core.informal"
    sys.modules[module.__name__] = module
    exec(compile(baseline_source, SOURCE, "exec"), module.__dict__)

    key = derive_encryption_key(os.environ["TEXT_CONFIG_PASSPHRASE"])
    definitions = load_extract_definitions(
        ROOT / "argumentation_analysis/data/extract_sources.json.gz.enc", key
    )
    before_detector = module.TaxonomySophismDetector()
    after_detector = TaxonomySophismDetector()
    head = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
    ).strip()
    print(
        f"taxonomy-name comparison | HEAD={head} baseline={args.baseline} "
        "| command=python scripts/compare_taxonomy_name_2812.py "
        f"--baseline {args.baseline} | output=aggregates-only",
        flush=True,
    )
    totals = dict(
        documents=0,
        before=0,
        after=0,
        key_difference=0,
        score_difference=0,
        newly_named=0,
    )
    for definition in definitions:
        text = definition.get("full_text", "")
        if not text:
            continue
        totals["documents"] += 1
        before = before_detector.detect_sophisms_from_taxonomy(text)
        after = after_detector.detect_sophisms_from_taxonomy(text)
        before_scores = {hit["taxonomy_key"]: hit["confidence"] for hit in before}
        after_scores = {hit["taxonomy_key"]: hit["confidence"] for hit in after}
        totals["before"] += len(before)
        totals["after"] += len(after)
        totals["key_difference"] += len(before_scores.keys() ^ after_scores.keys())
        totals["score_difference"] += sum(
            before_scores[pk] != after_scores[pk]
            for pk in before_scores.keys() & after_scores.keys()
        )
        totals["newly_named"] += sum(bool(hit["name"]) for hit in after) - sum(
            bool(hit["name"]) for hit in before
        )
    if not totals["documents"] or not totals["before"]:
        raise AssertionError("Comparison must exercise a non-empty detection baseline")
    print(
        "corpus aggregate: "
        + " ".join(f"{key}={value}" for key, value in totals.items()),
        flush=True,
    )
    if totals["key_difference"] or totals["score_difference"]:
        raise AssertionError("Taxonomy detection changed on the evaluation corpus")


if __name__ == "__main__":
    main()
