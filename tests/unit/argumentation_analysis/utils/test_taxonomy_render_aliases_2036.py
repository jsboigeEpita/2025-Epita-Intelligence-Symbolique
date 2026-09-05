"""#2036 item 2 — attested display aliases for the broken-register node names.

Arbitration (issue #2036): option 3 (display-only alias) with the added
constraint that an alias must be *attested*, never *forged*. Of the 8 « sûrs »
whose ``text_fr`` carries a broken register (argot calques, hyphenated
phrases), the domain literature attests a French rendering for 4:

* PK 320 « Appel aux têtes blondes » → « Pensez aux enfants »
  (fr.wikipedia.org/wiki/Pensez_aux_enfants — the cliché's rhetoric name,
  argumentum ad misericordiam).
* PK 328 « Facteur beurk » → « Sagesse du dégoût »
  (fr.wikipedia.org/wiki/Sagesse_du_dégoût — published French title of
  Kass's « wisdom of repugnance »).
* PK 449 « Un-peu-c'est-mieux-que-rien » → « Mieux vaut peu que rien »
  (attested French proverb, linternaute.fr/proverbe/2008 & dicocitations).
* PK 1311 « Plus c'est gros, plus ça passe » → « Gros mensonge »
  (attested rendering of « big lie » — fr.wikipedia.org Glossaire de la
  langue du Troisième Reich; Linguee/Reverso « big lie » = « gros mensonge »).

The other 4 « sûrs » (PK 41, 980, 992, 1009) keep their names: no attested
term found — better an ugly faithful name than an elegant invented one.

The alias is DISPLAY-ONLY: it applies where a node's name is resolved for a
reader or an LLM (detector state writes, benchmark name preference,
navigator prompt renders). The matching fields (``text_fr``,
``nom_vulgarisé``, ``Name`` as loaded) stay byte-identical — the lexical
matcher reads them, so an alias in the loaded data would change what
matches.
"""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import MagicMock, patch

import semantic_kernel as sk

from argumentation_analysis.paths import DATA_DIR

REAL_CSV = Path(DATA_DIR) / "argumentum_fallacies_taxonomy.csv"


def _real_csv_rows() -> list:
    with open(REAL_CSV, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _real_detector():
    """A TaxonomySophismDetector wired to the REAL taxonomy dataframe.

    The detector news up its own InformalAnalysisPlugin (kernel-required);
    the factory path not passing a kernel is a pre-existing latent issue
    (#2041 sweep), so the test injects a real plugin built like production
    builds it — real CSV through the loader chain (purge included).
    """
    from argumentation_analysis.agents.core.informal import (
        taxonomy_sophism_detector as tsd,
    )
    from argumentation_analysis.agents.core.informal.informal_definitions import (
        InformalAnalysisPlugin,
    )

    real_plugin = InformalAnalysisPlugin(
        kernel=MagicMock(spec=sk.Kernel), taxonomy_file_path=str(REAL_CSV)
    )
    with patch.object(tsd, "InformalAnalysisPlugin", return_value=real_plugin):
        return tsd.TaxonomySophismDetector(taxonomy_file_path=str(REAL_CSV))


class TestAliasTableIsAliveAndSourced:
    """A dead alias (PK absent from the data) would be a silent no-op, and an
    unsourced alias would violate the arbitration — both must fail loudly."""

    def test_every_aliased_pk_exists_in_the_csv(self):
        from argumentation_analysis.utils.taxonomy_local_overrides import (
            RENDER_ALIASES,
        )

        rows = _real_csv_rows()
        present = {r["PK"] for r in rows}
        for pk in RENDER_ALIASES:
            assert str(pk) in present, (
                f"PK {pk} is aliased but absent from the vendored CSV — "
                "the alias is dead"
            )

    def test_every_alias_has_a_cited_source(self):
        from argumentation_analysis.utils.taxonomy_local_overrides import (
            RENDER_ALIASES,
            RENDER_ALIAS_SOURCES,
        )

        assert set(RENDER_ALIAS_SOURCES) == set(RENDER_ALIASES), (
            "RENDER_ALIAS_SOURCES must cite a source for exactly the "
            "aliased PKs — an alias without a source is a forged name"
        )
        for pk, source in RENDER_ALIAS_SOURCES.items():
            assert (
                isinstance(source, str) and source.strip()
            ), f"PK {pk} alias carries an empty source citation"

    def test_alias_actually_renames_something(self):
        from argumentation_analysis.utils.taxonomy_local_overrides import (
            RENDER_ALIASES,
        )

        rows = {r["PK"]: r for r in _real_csv_rows()}
        for pk, alias in RENDER_ALIASES.items():
            current = rows[str(pk)]["text_fr"]
            assert alias.strip() != current.strip(), (
                f"PK {pk} alias {alias!r} equals the current text_fr — "
                "a no-op entry rots in the table"
            )


class TestDetectorWritesAliasedName:
    """The detector's state/pattern writes carry the attested alias as the
    node's display name, while the identity fields stay canonical."""

    def test_lexical_detection_of_pk320_carries_the_alias(self):
        detector = _real_detector()
        # « appel », « têtes », « blondes » are three >4-char text_fr words —
        # exactly the lexical bar (3 × 0.1 ≥ 0.3).
        detections = detector.detect_sophisms_from_taxonomy(
            "Un appel aux têtes blondes classique."
        )
        hit = next(d for d in detections if d["taxonomy_key"] == 320)
        assert hit["nom_vulgarise"] == "Pensez aux enfants", (
            "#2036 item 2: a detection of PK 320 must carry the attested "
            f"alias as its display name, got {hit['nom_vulgarise']!r}"
        )
        # Identity fields stay canonical — the alias never rewrites what the
        # node IS, only how its name reaches a reader.
        assert hit["description"] == "Appel aux têtes blondes"

    def test_pattern_search_of_pk328_carries_the_alias(self):
        detector = _real_detector()
        hits = detector.search_sophisms_by_pattern("beurk")
        hit = next(h for h in hits if h["taxonomy_key"] == 328)
        assert (
            hit["nom_vulgarise"] == "Sagesse du dégoût"
        ), f"PK 328 pattern hit must carry the alias, got {hit['nom_vulgarise']!r}"
        assert hit["description"] == "Facteur beurk"

    def test_non_aliased_detection_is_passthrough(self):
        detector = _real_detector()
        # A borderline node (PK 885 « Prêcher le faux pour savoir le vrai »)
        # is deliberately NOT aliased — its detection must echo the CSV value.
        hits = detector.search_sophisms_by_pattern("prêcher le faux")
        hit = next(h for h in hits if h["taxonomy_key"] == 885)
        value = hit["nom_vulgarise"]
        # empty upstream (pandas NaN through the DF path), stays unaliased
        assert value == "" or value != value


class TestBenchmarkNamePreference:
    """The benchmark resolves the reader-facing name of a node (the R924
    leak surface) — the alias must win over the text_fr preference."""

    def test_display_name_of_pk328_is_the_alias(self):
        from argumentation_analysis.evaluation.fallacy_benchmark import (
            FallacyBenchmarkRunner,
            _display_name,
        )

        runner = FallacyBenchmarkRunner()
        node = runner.node_map["328"]
        assert _display_name(node) == "Sagesse du dégoût"

    def test_display_name_of_non_aliased_node_is_text_fr(self):
        from argumentation_analysis.evaluation.fallacy_benchmark import (
            FallacyBenchmarkRunner,
            _display_name,
        )

        runner = FallacyBenchmarkRunner()
        node = runner.node_map["885"]
        assert _display_name(node) == node["text_fr"]

    def test_loaded_matching_fields_are_untouched(self):
        from argumentation_analysis.evaluation.fallacy_benchmark import (
            FallacyBenchmarkRunner,
        )
        from argumentation_analysis.utils.taxonomy_local_overrides import (
            RENDER_ALIASES,
        )

        runner = FallacyBenchmarkRunner()
        for pk in RENDER_ALIASES:
            node = runner.node_map[str(pk)]
            assert node["text_fr"] in (
                "Appel aux têtes blondes",
                "Facteur beurk",
                "Un-peu-c’est-mieux-que-rien",
                "Plus c’est gros, plus ça passe",
            ), f"PK {pk} text_fr drifted from the upstream mirror: {node['text_fr']!r}"


class TestNavigatorRendersAliasedName:
    """Navigator prompt renders are name surfaces — the alias applies."""

    @staticmethod
    def _navigator():
        from argumentation_analysis.agents.utils.taxonomy_navigator import (
            TaxonomyNavigator,
        )

        with open(REAL_CSV, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return TaxonomyNavigator(rows)

    def test_branch_str_of_pk328_shows_the_alias(self):
        nav = self._navigator()
        branch = nav.get_branch_as_str("328")
        assert (
            "Sagesse du dégoût" in branch
        ), f"navigator branch render must show the alias, got: {branch!r}"
        assert "Facteur beurk" not in branch

    def test_preview_shows_the_alias_not_the_calque(self):
        nav = self._navigator()
        preview = nav.get_taxonomy_preview(depth=6)
        assert "Sagesse du dégoût" in preview
        assert "Facteur beurk" not in preview

    def test_non_aliased_branch_is_passthrough(self):
        nav = self._navigator()
        # PK 885 has an empty nom_vulgarisé — the render keeps its (pre-fix)
        # empty-name shape, and a by-design familial node (PK 5) keeps its
        # upstream vulgarisé verbatim.
        branch_885 = nav.get_branch_as_str("885")
        assert "Prêcher le faux pour savoir le vrai" not in branch_885  # never aliased
        assert "-  (ID: 885)" in branch_885
        branch_5 = nav.get_branch_as_str("5")
        assert "La tête dans le sable" in branch_5


class TestAliasHelperContract:
    def test_unknown_pk_returns_the_default(self):
        from argumentation_analysis.utils.taxonomy_local_overrides import (
            render_alias,
        )

        assert render_alias("885", "Prêcher le faux pour savoir le vrai") == (
            "Prêcher le faux pour savoir le vrai"
        )

    def test_malformed_pk_returns_the_default(self):
        from argumentation_analysis.utils.taxonomy_local_overrides import (
            render_alias,
        )

        assert render_alias(None, "X") == "X"
        assert render_alias("not-a-pk", "X") == "X"
        assert render_alias("", "X") == "X"
