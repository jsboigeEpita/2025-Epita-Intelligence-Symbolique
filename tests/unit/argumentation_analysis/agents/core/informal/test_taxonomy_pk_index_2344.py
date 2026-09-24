"""The taxonomy loads with a usable PK index, or not at all (#2344).

Every reader of the taxonomy goes through ``df.loc[pk]``. The loader used to
log an error and carry on in two cases: primary keys that are null after
conversion (the frame was indexed on a nullable column holding ``<NA>``), and a
failing ``set_index`` (the frame came back with no PK index at all). Both then
failed far from their cause, in whichever lookup ran first. Duplicate keys were
not checked, and ``.loc`` returns a frame instead of a row for them.
"""

import pandas as pd
import pytest

from argumentation_analysis.agents.core.informal.informal_definitions import (
    InformalAnalysisPlugin,
)


def _load(tmp_path, rows):
    path = tmp_path / "taxonomy.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    plugin = InformalAnalysisPlugin(taxonomy_file_path=str(path))
    return plugin._get_taxonomy_dataframe()


def test_valid_taxonomy_is_indexed_by_pk(tmp_path):
    df = _load(
        tmp_path,
        [
            {"PK": 0, "FK_Parent": None, "text_fr": "Racine"},
            {"PK": 1, "FK_Parent": 0, "text_fr": "Enfant"},
        ],
    )
    assert df.index.name == "PK"
    assert df.loc[1, "text_fr"] == "Enfant"


def test_null_primary_key_refuses_to_load(tmp_path):
    rows = [
        {"PK": 0, "FK_Parent": None, "text_fr": "Racine"},
        {"PK": None, "FK_Parent": 0, "text_fr": "Sans clé"},
    ]
    with pytest.raises(ValueError, match="PK"):
        _load(tmp_path, rows)


def test_non_numeric_primary_key_refuses_to_load(tmp_path):
    rows = [
        {"PK": 0, "FK_Parent": None, "text_fr": "Racine"},
        {"PK": "un", "FK_Parent": 0, "text_fr": "Clé illisible"},
    ]
    with pytest.raises(ValueError, match="PK"):
        _load(tmp_path, rows)


def test_duplicate_primary_key_refuses_to_load(tmp_path):
    rows = [
        {"PK": 0, "FK_Parent": None, "text_fr": "Racine"},
        {"PK": 1, "FK_Parent": 0, "text_fr": "Premier"},
        {"PK": 1, "FK_Parent": 0, "text_fr": "Doublon"},
    ]
    with pytest.raises(ValueError, match=r"doublons : \[1\]"):
        _load(tmp_path, rows)


def test_missing_primary_key_column_refuses_to_load(tmp_path):
    with pytest.raises(ValueError, match="PK"):
        _load(tmp_path, [{"id": 0, "text_fr": "Racine"}])


def test_the_real_taxonomy_still_loads():
    df = InformalAnalysisPlugin()._get_taxonomy_dataframe()
    assert df.index.name == "PK"
    assert df.index.is_unique
    assert not df.index.isna().any()
