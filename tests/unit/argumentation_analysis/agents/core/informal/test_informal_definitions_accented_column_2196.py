"""#2196 — born-red guard: the plugin must read the column the taxonomy actually has.

`informal_definitions.py` reads `nom_vulgarise` (**unaccented**) — a column no
shipped CSV ever carried. Measured: `git log --all -S 'nom_vulgarise' -- '*.csv'`
returns nothing, and the delivered 1408×103 taxonomy carries `nom_vulgarisé`
alone (neither `nom_vulgarise` nor `Name`). The four reads therefore fall through
to their `""` / `"N/A"` default on **every** row, and the two column guards
(`:529`, `:693`) are `if "nom_vulgarise" in df.columns:` — a condition that is
**always false**, so the branches they protect have never run.

Origin: `0b77c3e50` (2025-06-24) « Harmonise l'utilisation de la clé
'nom_vulgarise' » replaced the *accented column access* **together with** the
*dictionary key* in one sweep. The key change was right — the output contract is
unaccented, and this guard asserts it stays so. The column change was not: a
dict key and a CSV column are two different names with two different owners, and
the CSV never followed the commit.

Why nobody saw it: the defect **preserves the field name and its type**. A named
row comes out as an empty `str`, not an error, so no downstream reader can tell
« row without a name » from « column misspelt ».

Severity, measured on the delivered taxonomy: 40 rows carry a non-NaN
`nom_vulgarisé`, and **39 of them differ from `text_fr`** (pk=5: name « La tête
dans le sable » vs text_fr « Ignorance délibérée »). A named row is thus
anonymous through the hierarchy/details/summary paths, unfindable by its
vulgarised name, and `find_fallacy_definition` reports `text_fr` as if it were
the name.
"""

import json
import re

import pandas as pd
import pytest
from semantic_kernel import Kernel

from argumentation_analysis.agents.core.informal.informal_definitions import (
    InformalAnalysisPlugin,
)

NAME_COL = "nom_vulgarisé"  # la colonne que la taxonomie porte réellement
OUTPUT_KEY = "nom_vulgarise"  # la clé du contrat de sortie (non accentuée)
_META = re.compile(r"[.*+?^${}()|\[\]\\]")


@pytest.fixture(scope="module")
def plugin() -> InformalAnalysisPlugin:
    """Le plugin réel sur la taxonomie réelle."""
    return InformalAnalysisPlugin(kernel=Kernel(), taxonomy_file_path=None)


@pytest.fixture(scope="module")
def df(plugin):
    return plugin._get_taxonomy_dataframe()


@pytest.fixture(scope="module")
def named_rows(df):
    """Les lignes réellement nommées, utilisables comme motif de recherche."""
    rows = []
    for pk, row in df[df[NAME_COL].notna()].iterrows():
        name = str(row[NAME_COL]).strip()
        if name and not _META.search(name):
            rows.append((int(pk), name))
    return rows


@pytest.fixture(scope="module")
def name_only_rows(df, named_rows):
    """Les lignes nommées introuvables par `text_fr` ni `Latin` : le rouge le plus net."""
    out = []
    for pk, name in named_rows:
        row = df.loc[pk]
        text = str(row.get("text_fr", "")).lower()
        latin = str(row.get("Latin", "")).lower()
        if name.lower() not in text and name.lower() not in latin:
            out.append((pk, name))
    return out


def test_instrument_has_named_rows_to_work_with(named_rows, name_only_rows):
    """Non-vacuité : l'instrument a une population. Un garde sans population est vert à vide."""
    assert (
        len(named_rows) > 0
    ), "instrument : la taxonomie doit porter des lignes nommées"
    assert (
        len(name_only_rows) > 0
    ), "instrument : il faut au moins une ligne nommée introuvable par text_fr/Latin"


class TestPluginPathsCarryTheRealName:
    """Les 4 lectures à défaut vide + le résumé doivent rendre le nom réel."""

    def test_explore_hierarchy_current_node_carries_the_name(
        self, plugin, df, name_only_rows
    ):
        pk, expected = name_only_rows[0]
        node = plugin._internal_explore_hierarchy(
            current_pk=pk, df=df, max_children=20
        )["current_node"]
        assert node[OUTPUT_KEY] == expected, (
            f"pk={pk} : le nœud doit porter {expected!r}, obtenu {node[OUTPUT_KEY]!r} "
            f"— la lecture tape une colonne absente (#2196)"
        )

    def test_explore_hierarchy_child_carries_the_name(self, plugin, df):
        """Le chemin enfant (`:281`) doit porter le nom réel quand il en a un."""
        pairs = []
        for pk in df.index:
            res = plugin._internal_explore_hierarchy(
                current_pk=int(pk), df=df, max_children=20
            )
            for child in res.get("children", []):
                cell = df.loc[child["pk"], NAME_COL]
                if pd.notna(cell) and str(cell).strip():
                    pairs.append((child["pk"], str(cell).strip(), child[OUTPUT_KEY]))
            if pairs:
                break
        assert pairs, "instrument : au moins un enfant nommé doit exister"
        child_pk, real, got = pairs[0]
        assert (
            got == real
        ), f"enfant pk={child_pk} : attendu {real!r}, obtenu {got!r} (#2196)"

    def test_node_details_parent_carries_the_name(self, plugin, df, name_only_rows):
        """`_internal_get_node_details` (`:350`) doit porter le nom du parent réel."""
        target = None
        for pk, _ in name_only_rows:
            res = plugin._internal_get_node_details(pk=pk, df=df)
            parent = res.get("parent")
            if parent and parent.get("pk") is not None:
                parent_row = df.loc[parent["pk"]]
                real = parent_row.get(NAME_COL)
                if isinstance(real, str) and real.strip():
                    target = (int(parent["pk"]), real.strip(), parent[OUTPUT_KEY])
                    break
        assert (
            target
        ), "instrument : au moins un nœud nommé avec parent nommé doit exister"
        pk, real, got = target
        assert got == real, f"parent pk={pk} : attendu {real!r}, obtenu {got!r} (#2196)"

    def test_summary_for_prompt_carries_names(self, plugin, name_only_rows):
        """`:412` : le résumé rendait « N/A » pour **toutes** les lignes."""
        summary = plugin.get_taxonomy_summary_for_prompt()
        missing = [name for _, name in name_only_rows[:5] if name not in summary]
        assert not missing, (
            f"{len(missing)} nom(s) absents du résumé — ex. {missing[0]!r}. "
            f"Le défaut rend 'N/A' partout (#2196)"
        )


class TestSearchNoLongerSkipsTheNameColumn:
    """Les gardes `:529`/`:693` sont toujours fausses : la branche n'a jamais tourné."""

    def test_definition_found_by_vulgarised_name(self, plugin, name_only_rows):
        pk, name = name_only_rows[0]
        payload = json.loads(plugin.find_fallacy_definition(name))
        assert payload.get("pk") == pk, (
            f"« {name} » (pk={pk}) doit être trouvable par son nom vulgarisé, "
            f"obtenu {payload.get('pk')!r} / {payload.get('error')!r} (#2196)"
        )

    def test_example_found_by_vulgarised_name(self, plugin, name_only_rows):
        pk, name = name_only_rows[0]
        payload = json.loads(plugin.get_fallacy_example(name))
        assert payload.get("pk") == pk, (
            f"« {name} » (pk={pk}) doit être trouvable par son nom vulgarisé, "
            f"obtenu {payload.get('pk')!r} / {payload.get('error')!r} (#2196)"
        )

    def test_reported_name_is_the_vulgarised_one(
        self, plugin, df, named_rows, name_only_rows
    ):
        """`:569` isolé du reste : on cherche par un canal qui **trouve déjà**
        (`text_fr`), et on vérifie seulement le nom **rapporté**.

        Sans cette isolation, un rouge pourrait venir de « pas trouvé du tout »
        au lieu de « trouvé, mais nommé `text_fr` ».
        """
        found = None
        for pk, name in name_only_rows:
            text = str(df.loc[pk].get("text_fr", "")).strip()
            if not text:
                continue
            payload = json.loads(plugin.find_fallacy_definition(text))
            if payload.get("pk") == pk:
                found = (pk, name, text, payload)
                break
        assert found, (
            "instrument : au moins une ligne nommée doit être joignable par son text_fr "
            "(canal déjà opérant) pour isoler le nom rapporté"
        )
        pk, name, text, payload = found
        assert payload["fallacy_name"] == name, (
            f"requête « {text} » → pk={pk} trouvé, mais le nom rapporté est "
            f"{payload['fallacy_name']!r} au lieu du nom vulgarisé {name!r} (#2196)"
        )


class TestInstrumentDiscriminates:
    """Contrôle positif ET négatif de l'instrument de recensement.

    Un instrument qui rend la même valeur sur toute population ne mesure pas la
    population : on prouve ici qu'il sait rendre **trouvé** et **non trouvé**.
    """

    @staticmethod
    def _reachable_count(plugin, rows):
        n = 0
        for pk, name in rows:
            if json.loads(plugin.find_fallacy_definition(name)).get("pk") == pk:
                n += 1
        return n

    def test_positive_control_some_named_row_is_reachable(self, plugin, name_only_rows):
        found = self._reachable_count(plugin, name_only_rows[:5])
        assert found > 0, (
            "contrôle positif : au moins une ligne nommée doit être joignable par son "
            "nom — sinon l'instrument est un zéro constant (#2196)"
        )

    def test_negative_control_a_made_up_name_is_not_found(self, plugin):
        payload = json.loads(
            plugin.find_fallacy_definition("zzz_sophisme_inexistant_zzz")
        )
        assert "error" in payload, (
            "contrôle négatif : un nom inexistant doit rendre un payload d'erreur, "
            f"obtenu {payload!r}"
        )

    def test_control_the_text_channel_still_works(self, plugin, name_only_rows):
        """Témoin : le canal `text_fr` cherchait déjà — il doit continuer.

        Sans ce témoin, un instrument cassé qui ne trouve rien du tout passerait
        pour un contrôle négatif réussi.
        """
        pk, name = name_only_rows[0]
        text = str(plugin._get_taxonomy_dataframe().loc[pk].get("text_fr", "")).strip()
        assert text, "instrument : la ligne témoin doit porter un text_fr"
        payload = json.loads(plugin.find_fallacy_definition(text))
        assert (
            payload.get("pk") == pk
        ), f"le canal text_fr doit rester opérant : « {text} » → {payload!r}"
