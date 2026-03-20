#!/usr/bin/env python3
"""Update baseline_corpus_v1.json with taxonomy mappings from taxonomy_mapping.json.

Transforms expected_fallacies from simple string lists to structured objects with
taxonomy_pk, taxonomy_family_pk, taxonomy_family_id, taxonomy_depth, and description.

Also replaces the ad-hoc 7 meta-families with the canonical 8 taxonomy families.

Issue: #136
"""
import json
import sys
from pathlib import Path

CORPUS_PATH = Path("argumentation_analysis/evaluation/corpus/baseline_corpus_v1.json")
MAPPING_PATH = Path("argumentation_analysis/evaluation/corpus/taxonomy_mapping.json")


def main():
    with open(MAPPING_PATH) as f:
        mapping_data = json.load(f)
    mappings = mapping_data["mappings"]

    with open(CORPUS_PATH) as f:
        corpus = json.load(f)

    # Build reverse family mapping: family_id -> list of corpus doc IDs
    taxonomy_family_coverage = {}

    for doc in corpus["documents"]:
        old_fallacies = doc.get("expected_fallacies", [])
        if not old_fallacies:
            # Clean docs or formal-only docs: add empty structured list
            doc["expected_fallacies_structured"] = []
            # Remove old ad-hoc fallacy_families if present
            doc.pop("fallacy_families", None)
            continue

        structured = []
        doc_families = set()
        for fallacy_type in old_fallacies:
            if fallacy_type not in mappings:
                print(f"WARNING: {fallacy_type} not in mapping (doc {doc['id']})")
                structured.append({
                    "type": fallacy_type,
                    "taxonomy_pk": None,
                    "taxonomy_family_pk": None,
                    "taxonomy_family_id": None,
                    "taxonomy_depth": None
                })
                continue

            m = mappings[fallacy_type]
            structured.append({
                "type": fallacy_type,
                "taxonomy_pk": m["taxonomy_pk"],
                "taxonomy_family_pk": m["taxonomy_family_pk"],
                "taxonomy_family_id": m["taxonomy_family_id"],
                "taxonomy_depth": m["taxonomy_depth"]
            })
            doc_families.add(m["taxonomy_family_id"])

            # Track coverage
            fam_id = m["taxonomy_family_id"]
            taxonomy_family_coverage.setdefault(fam_id, []).append(doc["id"])

        doc["expected_fallacies_structured"] = structured
        # Replace ad-hoc fallacy_families with taxonomy families
        doc["taxonomy_families"] = sorted(doc_families)
        doc.pop("fallacy_families", None)

    # Update metadata
    meta = corpus["metadata"]

    # Replace ad-hoc fallacy_family_coverage with taxonomy-based
    meta["taxonomy_family_coverage"] = {
        fam_id: sorted(set(docs))
        for fam_id, docs in sorted(taxonomy_family_coverage.items())
    }

    # Keep old coverage for reference but mark deprecated
    if "fallacy_family_coverage" in meta:
        meta["_deprecated_fallacy_family_coverage"] = meta.pop("fallacy_family_coverage")

    # Add taxonomy mapping reference
    meta["taxonomy_mapping_version"] = mapping_data.get("_version", "1.0")
    meta["taxonomy_source"] = "argumentation_analysis/data/taxonomy_full.json"

    # Update version
    corpus["corpus_version"] = "1.1"
    meta["corpus_version_notes"] = (
        "v1.1 — added taxonomy_pk mappings for all 23 fallacy types (#136). "
        "Each expected_fallacy now has structured form with taxonomy_pk, "
        "taxonomy_family_pk, taxonomy_family_id, and taxonomy_depth. "
        "Replaced 7 ad-hoc meta-families with 6 canonical taxonomy families. "
        "Previous: " + meta.get("corpus_version_notes", "")
    )

    # Write updated corpus
    with open(CORPUS_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Updated {CORPUS_PATH}")
    print(f"  Documents: {len(corpus['documents'])}")
    print(f"  Taxonomy families covered: {sorted(taxonomy_family_coverage.keys())}")
    print(f"  Fallacy types mapped: {len(mappings)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
