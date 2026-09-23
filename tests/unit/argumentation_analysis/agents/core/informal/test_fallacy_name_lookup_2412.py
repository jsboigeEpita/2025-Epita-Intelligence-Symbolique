"""#2412 — a fallacy name finds its own node, and a name that designates several says so.

``find_fallacy_definition`` and ``get_fallacy_example`` are the informal
agent's lookups by name. They read the query as a regex and returned the first
substring hit: on ``main`` ``e1d9b5b6``, 3 of the taxonomy's own ``text_fr``
names were not found (parentheses read as a group) and 10 unique names resolved
to another node (an earlier row contains them). A name carried by several rows
came back as one arbitrary definition.

The population is the real CSV, not a fixture: a fixture only holds the shapes
its author thought of, and the defect lived in the ones nobody wrote.
"""

import json
import math

import pytest
from semantic_kernel import Kernel

from argumentation_analysis.agents.core.informal.informal_definitions import (
    InformalAnalysisPlugin,
    rows_matching_fallacy_name,
)


@pytest.fixture(scope="module")
def plugin() -> InformalAnalysisPlugin:
    return InformalAnalysisPlugin(kernel=Kernel(), taxonomy_file_path=None)


@pytest.fixture(scope="module")
def df(plugin):
    return plugin._get_taxonomy_dataframe()


@pytest.fixture(scope="module")
def unique_names(df):
    """``(pk, text_fr)`` for every row whose name no other name column repeats."""
    folded = {}
    for column in ("nom_vulgarisé", "text_fr", "Latin"):
        for pk, value in df[column].dropna().astype(str).items():
            folded.setdefault(value.strip().casefold(), set()).add(pk)
    out = []
    for pk, value in df["text_fr"].dropna().astype(str).items():
        name = value.strip()
        if name and folded[name.casefold()] == {pk}:
            out.append((int(pk), name))
    return out


def test_population_is_the_real_taxonomy(df, unique_names):
    """Non-vacuity: the guard runs over the CSV, not over an empty list."""
    assert len(df) > 1000
    assert len(unique_names) > 1000


def test_every_unique_name_finds_its_own_node(plugin, unique_names):
    """Born red on ``main``: 13 failures (3 not found, 10 another node)."""
    wrong = []
    for pk, name in unique_names:
        payload = json.loads(plugin.find_fallacy_definition(name))
        if payload.get("pk") != pk:
            wrong.append((pk, payload.get("pk"), payload.get("error")))
    assert not wrong, (
        f"{len(wrong)} unique names do not resolve to their own node "
        f"(pk, got pk, error): {wrong[:15]}"
    )


def test_example_lookup_shares_the_resolution(plugin, unique_names):
    """The example lookup is the same lookup: it resolves the same names."""
    wrong = [
        pk
        for pk, name in unique_names
        if json.loads(plugin.get_fallacy_example(name)).get("pk") != pk
    ]
    assert (
        not wrong
    ), f"example lookup resolves {len(wrong)} names elsewhere: {wrong[:15]}"


def test_a_name_with_regex_metacharacters_is_matched_literally(df):
    names = [
        (pk, str(v).strip())
        for pk, v in df["text_fr"].dropna().items()
        if any(c in str(v) for c in "()[]?*+.")
    ]
    assert names, "instrument: the taxonomy must carry names with metacharacters"
    for pk, name in names:
        assert pk in rows_matching_fallacy_name(df, name).index, (pk, name)


def test_a_shared_name_reports_its_candidates(plugin, df):
    """A name carried by several rows does not pick one: it lists them."""
    counts = (
        df["text_fr"].dropna().astype(str).str.strip().str.casefold().value_counts()
    )
    shared = counts[counts > 1].index[0]
    rows = df[df["text_fr"].fillna("").astype(str).str.strip().str.casefold() == shared]
    payload = json.loads(plugin.find_fallacy_definition(rows.iloc[0]["text_fr"]))
    assert payload.get("ambiguous") is True
    assert "pk" not in payload, "an ambiguous name must not be answered with one node"
    assert {c["pk"] for c in payload["candidates"]} >= set(int(pk) for pk in rows.index)


def test_a_keyword_reports_several_candidates_capped(plugin):
    """The prompt's keyword use: a broad term returns candidates, capped at 10."""
    payload = json.loads(plugin.find_fallacy_definition("appel"))
    assert payload.get("ambiguous") is True
    assert payload["match_count"] > len(payload["candidates"]) == 10


def test_reported_name_is_never_nan(plugin, df):
    """A row without ``nom_vulgarisé`` is reported under its ``text_fr``.

    ``row.get("nom_vulgarisé", fallback)`` returned the empty cell, ``NaN``, and
    the fallback never fired: the agent received ``"fallacy_name": NaN``.
    """
    pk, name = next(
        (int(pk), str(row["text_fr"]).strip())
        for pk, row in df[df["nom_vulgarisé"].isna()].iterrows()
        if len(rows_matching_fallacy_name(df, str(row["text_fr"]))) == 1
    )
    raw = plugin.find_fallacy_definition(name)
    assert "NaN" not in raw, raw
    assert json.loads(raw)["fallacy_name"] == name


def test_category_listing_names_are_never_nan(plugin, df):
    family = df["Famille"].dropna().iloc[0]
    fallacies = json.loads(plugin.list_fallacies_in_category(family))["fallacies"]
    assert fallacies
    for entry in fallacies:
        name = entry["nom_vulgarise"]
        assert isinstance(name, str) and name, entry
        assert not (isinstance(name, float) and math.isnan(name))


def test_negative_control_an_unknown_name_is_an_error(plugin):
    payload = json.loads(plugin.find_fallacy_definition("zzz_sophisme_inexistant_zzz"))
    assert "error" in payload and "pk" not in payload
