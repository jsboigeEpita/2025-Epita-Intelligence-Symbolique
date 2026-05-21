"""Tests for Track PP (#665): Extended fallacy counter + family-level counting.

Tests cover:
  1. Extended counter recognizes taxonomy-specific names
  2. Family counter parses Section 3 headers correctly
  3. Before/after measurement improvement
"""

import pytest

from scripts.scda_deepsynthesis_vs_baseline import (
    count_named_fallacies_with_taxonomy,
    count_fallacy_families,
    analyze_report,
)

# --- Sample report text for testing ---
SAMPLE_REPORT = """## 2. Argument Mapping
| arg_1 | pro | premisses: X Y Z | fallacy_fallacy_1 |

## 3. Fallacy Diagnosis by Family

### fallacy_1: causal — `fallacy/causal/Post hoc, ergo propter hoc`
This is a post hoc fallacy.

### fallacy_2: presumption — `fallacy/presumption/Enthymême invalide`
The argument has an invalid enthymeme.

### fallacy_3: relevance — `fallacy/relevance/Appel au racisme`
Appel au racisme detected.

### fallacy_4: inductive — `fallacy/inductive/Généralisation hâtive`
Hasty generalization found.

### fallacy_5: ambiguity — `fallacy/ambiguity/Tromperie implicite`
Implicit deception.

### fallacy_6: other — `fallacy/other/Hyperbole`
Exaggeration present.

## 4. Convergent Verdicts
Some convergence text.
"""


class TestExtendedCounter:
    """Extended counter recognizes taxonomy-specific names."""

    def test_standard_names(self):
        found = count_named_fallacies_with_taxonomy(
            "Ad hominem and Slippery slope detected."
        )
        names = {f["name"] for f in found}
        assert "Ad hominem" in names
        assert "Slippery slope" in names

    def test_taxonomy_specific_names(self):
        found = count_named_fallacies_with_taxonomy(
            "Enthymême invalide detected in the argument."
        )
        names = {f["name"] for f in found}
        assert "Enthymême invalide" in names

    def test_taxonomy_relevance_names(self):
        found = count_named_fallacies_with_taxonomy(
            "Appel au racisme and Appel à la panique morale found."
        )
        names = {f["name"] for f in found}
        assert "Appel au racisme" in names
        assert "Appel à la panique morale" in names

    def test_corpus_c_taxonomy_names(self):
        found = count_named_fallacies_with_taxonomy(
            "Appel au nationalisme and Reductio ad Hitlerum identified."
        )
        names = {f["name"] for f in found}
        assert "Appel au nationalisme" in names
        assert "Reductio ad Hitlerum" in names

    def test_no_false_positives(self):
        found = count_named_fallacies_with_taxonomy(
            "This is a normal text with no fallacy references."
        )
        assert len(found) == 0

    def test_has_taxonomy_flag(self):
        found = count_named_fallacies_with_taxonomy(
            "### fallacy_1: causal — `fallacy/causal/Post hoc`"
        )
        assert len(found) > 0
        assert all(f["has_taxonomy"] for f in found)


class TestFamilyCounter:
    """Family counter parses Section 3 headers correctly."""

    def test_all_five_families(self):
        families = count_fallacy_families(SAMPLE_REPORT)
        assert families["causal"] == 1
        assert families["presumption"] == 1
        assert families["relevance"] == 1
        assert families["inductive"] == 1
        assert families["ambiguity"] == 1
        assert families["other"] == 1

    def test_empty_text(self):
        families = count_fallacy_families("")
        assert all(v == 0 for v in families.values())

    def test_no_section3(self):
        families = count_fallacy_families("Some text without fallacy headers.")
        assert all(v == 0 for v in families.values())

    def test_multiple_same_family(self):
        text = (
            "### fallacy_1: causal — `fallacy/causal/Post hoc`\n"
            "### fallacy_2: causal — `fallacy/causal/Non sequitur`\n"
            "### fallacy_3: relevance — `fallacy/relevance/Ad hominem`\n"
        )
        families = count_fallacy_families(text)
        assert families["causal"] == 2
        assert families["relevance"] == 1

    def test_distinct_family_count(self):
        families = count_fallacy_families(SAMPLE_REPORT)
        active = {k: v for k, v in families.items() if v > 0 and k != "other"}
        assert len(active) == 5


class TestAnalyzeReportIntegration:
    """analyze_report includes both named fallacies and family counts."""

    def test_includes_fallacy_families_key(self):
        result = analyze_report(SAMPLE_REPORT)
        assert "fallacy_families" in result
        assert isinstance(result["fallacy_families"], dict)

    def test_includes_named_fallacies(self):
        result = analyze_report(SAMPLE_REPORT)
        assert "named_fallacies" in result
        names = {f["name"] for f in result["named_fallacies"]}
        assert "Post hoc" in names

    def test_family_count_matches(self):
        result = analyze_report(SAMPLE_REPORT)
        families = result["fallacy_families"]
        active = {k: v for k, v in families.items() if v > 0 and k != "other"}
        assert len(active) >= 3


class TestBeforeAfterMeasurement:
    """Verify the extended counter improves measurement over the original 34-item list."""

    def test_extended_finds_more_than_standard(self):
        """Extended counter should find at least as many as the old 34-item list."""
        text_with_taxonomy = (
            "Enthymême invalide detected. "
            "Appel au racisme found. "
            "Pseudorationalisme identified."
        )
        found = count_named_fallacies_with_taxonomy(text_with_taxonomy)
        names = {f["name"] for f in found}
        # These taxonomy names were NOT in the original 34-item list
        assert "Enthymême invalide" in names
        assert "Appel au racisme" in names
        assert "Pseudorationalisme" in names
        assert len(found) >= 3
