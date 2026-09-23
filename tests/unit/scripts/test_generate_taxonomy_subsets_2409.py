"""#2409 — the subsets script reads the taxonomy's parent relation from its one reader.

`scripts/data_preparation/generate_taxonomy_subsets.py` found a node's children
with ``startswith(parent_path + ".") & depth == parent_depth + 1``. Measured
on ``main`` ``8fb36bb0`` with that rule: the root (path ``"0"``) had **0**
children, since the depth-1 nodes carry bare segments, and the one row whose
``depth`` cell disagrees with its path (6 segments, depth 7) was missing from
its parent's children. The subsets it writes did not change (the root's
children are already in ``small``, and that row is deeper than ``medium``),
so the last test pins that the repair keeps them identical to the tracked files.
"""

import csv
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "argumentation_analysis" / "data"


def _load_script():
    path = ROOT / "scripts" / "data_preparation" / "generate_taxonomy_subsets.py"
    spec = importlib.util.spec_from_file_location("generate_taxonomy_subsets", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script():
    return _load_script()


@pytest.fixture(scope="module")
def df(script):
    return script.load_and_prepare_taxonomy(
        str(DATA / "argumentum_fallacies_taxonomy.csv")
    )


def test_the_root_has_the_depth_1_nodes_as_children(script, df):
    root_path = str(df.loc[df["depth"] == 0, "path"].iloc[0])
    got = set(script.get_direct_children(df, root_path).index)
    assert got == set(df.index[df["depth"] == 1])
    assert len(got) == 7


def test_a_row_whose_depth_disagrees_with_its_path_keeps_its_parent(script, df):
    # oracle by string work: rows whose segment count is not depth + 1
    paths = df["path"].astype(str)
    odd = [
        pk
        for pk, path in paths.items()
        if df.loc[pk, "depth"] != path.count(".") + 1 and df.loc[pk, "depth"] != 0
    ]
    assert odd, "the CSV carries at least one such row (PK 824 measured)"
    for pk in odd:
        parent = paths[pk].rsplit(".", 1)[0]
        assert pk in script.get_direct_children(df, parent).index, pk


@pytest.mark.parametrize("name", ["small", "medium", "full"])
def test_the_subsets_keep_the_tracked_rows(script, tmp_path, name):
    script.generate_taxonomy_subsets(base_path=str(DATA), output_dir=str(tmp_path))
    with open(tmp_path / f"taxonomy_{name}.csv", encoding="utf-8") as handle:
        written = {row["PK"] for row in csv.DictReader(handle)}
    with open(DATA / f"taxonomy_{name}.csv", encoding="utf-8") as handle:
        tracked = {row["PK"] for row in csv.DictReader(handle)}
    assert written == tracked
