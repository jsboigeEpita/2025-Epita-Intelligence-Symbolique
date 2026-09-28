"""The taxonomy detector reads only columns in its loaded CSV (#2812)."""

import ast
import inspect
import textwrap

import pytest

from argumentation_analysis.agents.core.informal.taxonomy_sophism_detector import (
    TaxonomySophismDetector,
)
from argumentation_analysis.agents.core.informal.informal_definitions import (
    reported_fallacy_name,
)


@pytest.fixture(scope="module")
def detector():
    return TaxonomySophismDetector()


def test_detector_column_reads_exist_in_loaded_taxonomy(detector):
    columns = set(detector._get_taxonomy_df().columns)
    assert len(columns) > 5
    missing = set()
    for method_name in (
        "get_main_branches",
        "detect_sophisms_from_taxonomy",
        "_get_parent_context",
        "search_sophisms_by_pattern",
    ):
        method = getattr(TaxonomySophismDetector, method_name)
        tree = ast.parse(textwrap.dedent(inspect.getsource(method)))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in {"row", "sibling", "current_row"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and node.args[0].value not in columns
            ):
                missing.add((method_name, node.args[0].value))
    assert not missing, f"detector reads absent CSV columns: {sorted(missing)}"


def test_detected_name_is_reported_name_without_extra_name_match(detector):
    df = detector._get_taxonomy_df()
    named = df[df["nom_vulgarisé"].notna()]
    assert not named.empty
    pk = int(named.index[0])
    name = reported_fallacy_name(df.loc[pk])
    detections = detector.detect_sophisms_from_taxonomy(name, max_sophisms=len(df))
    matching = [d for d in detections if d["taxonomy_key"] == pk]
    assert matching
    assert matching[0]["name"] == name
    assert not any(
        "Nom officiel" in match for d in detections for match in d["matches"]
    )


def test_output_names_use_reported_name(detector):
    df = detector._get_taxonomy_df()
    branches = detector.get_main_branches()
    assert branches
    assert all(
        b["name"] == reported_fallacy_name(df.loc[b["taxonomy_key"]]) for b in branches
    )
    pk = int(df.index[df["depth"] == 1][0])
    siblings = detector._get_parent_context(pk)["siblings"]
    assert siblings
    assert all(
        s["name"] == reported_fallacy_name(df.loc[s["taxonomy_key"]]) for s in siblings
    )
    pattern = str(df.loc[pk, "Famille"])
    hits = detector.search_sophisms_by_pattern(pattern, max_results=len(df))
    assert hits
    assert all(
        h["name"] == reported_fallacy_name(df.loc[h["taxonomy_key"]]) for h in hits
    )
