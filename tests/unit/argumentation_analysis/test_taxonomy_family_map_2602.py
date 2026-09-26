# -*- coding: utf-8 -*-
"""#2602 — né-rouge : la carte familles de TaxonomyExplorerPlugin.

Deux défauts mesurés sur ``main`` :

1. **Accidents de sous-chaîne** — les ``patterns`` des familles sont cherchés
   comme sous-chaînes des champs du nœud, sans frontière de mot : ``oral``
   matche à l'intérieur de ``morale`` / ``temporalité`` dans ``text_fr``. Les 8
   nœuds ci-dessous sont tous classés ``audio_oral_context`` sur ``main`` alors
   que le seul hit est ce fragment.
2. **Couverture 68/1408** — sans héritage, 95 % de la taxonomie n'a pas de
   famille et chaque détection sur un nœud non mappé disparaît de l'analyse par
   famille (``get_family_statistics`` ne la porte nulle part, et
   ``analyze_comprehensive`` ne la compte pas).

Ce fichier utilise la vraie taxonomie (CSV versionné) : les PK cités sont des
constantes de ce fichier, choisis par mesure sur l'arbre courant.
"""

from unittest.mock import AsyncMock

import pytest

from argumentation_analysis.plugin_framework.core.plugins.standard.taxonomy_explorer.plugin import (
    TaxonomyExplorerPlugin,
)
from argumentation_analysis.agents.tools.analysis.fallacy_family_analyzer import (
    AnalysisDepth,
    FallacyFamily,
    FallacyFamilyAnalyzer,
)

# Nœuds dont ``text_fr`` contient le MOT « morale » : sur main, le fragment
# « oral » les classe audio_oral_context (score 0.3, le seuil exact).
MORALE_PKS = [117, 315, 339, 769, 922, 1163, 1182, 1321]
# « intimidation » mot entier dans text_fr : un vrai hit audio_oral_context,
# qui doit SURVIVRE à la frontière de mot (contrôle positif).
WHOLE_WORD_AUDIO_PK = 190
# nom_vulgarisé = « Diversion » : le seul mapping à preuve nom — lui et ses
# descendants sont la source d'héritage légitime.
DIVERSION_PK = 1314
# Descendant de 1314 : hérite diversion_attack (preuve nom à la racine).
INHERITS_DIVERSION_PK = 1321
# Descendant de 356 (« manipulation » dans text_fr seulement — preuve
# description au seuil) : son ancêtre n'est PAS une source d'héritage.
DESCRIPTION_ONLY_DESCENDANT_PK = 357


@pytest.fixture(scope="module")
def plugin() -> TaxonomyExplorerPlugin:
    return TaxonomyExplorerPlugin()


class TestWordBoundary:
    """Les patterns ne matchent plus à l'intérieur d'un autre mot."""

    def test_morale_nodes_leave_audio_oral(self, plugin):
        cache = plugin._family_mapping_cache
        offenders = {
            pk: cache.get(pk)
            for pk in MORALE_PKS
            if cache.get(pk) == "audio_oral_context"
        }
        assert not offenders, (
            f"des nœuds dont text_fr contient le mot 'morale' sont classés "
            f"audio_oral_context par le fragment 'oral' : {offenders}"
        )

    def test_whole_word_hit_still_maps(self, plugin):
        # « intimidation » mot entier doit continuer à mapper audio_oral_context.
        assert (
            plugin._family_mapping_cache.get(WHOLE_WORD_AUDIO_PK)
            == "audio_oral_context"
        )

    def test_diversion_vulgarised_keeps_its_family(self, plugin):
        # Forme que main traitait déjà correctement — elle ne doit pas bouger.
        assert plugin._family_mapping_cache.get(DIVERSION_PK) == "diversion_attack"


class TestAncestorInheritance:
    """L'héritage ne propage qu'une preuve au niveau du nom (#2602 review).

    51 des 52 mappings pattern ne tiennent que par un mot de description au
    seuil exact — en propager un remplacerait une absence honnête par un
    mauvais label (le nœud 356, « manipulation » dans text_fr, et ses 232
    descendants audio_oral_context).
    """

    def test_unmapped_descendant_inherits(self, plugin):
        cache = plugin._family_mapping_cache
        assert cache.get(INHERITS_DIVERSION_PK) == "diversion_attack", cache.get(
            INHERITS_DIVERSION_PK
        )

    def test_description_only_source_does_not_propagate(self, plugin):
        # 357 descend de 356, dont l'unique preuve est « manipulation » dans
        # text_fr : pas d'héritage — la détection y sera portée non classifiée.
        cache = plugin._family_mapping_cache
        assert DESCRIPTION_ONLY_DESCENDANT_PK not in cache, cache.get(
            DESCRIPTION_ONLY_DESCENDANT_PK
        )

    def test_no_mapped_ancestor_stays_out(self, plugin):
        # 117 : ni hit de pattern, ni ancêtre à preuve nom — pas de famille inventée.
        assert 117 not in plugin._family_mapping_cache

    def test_coverage_is_measured_and_published(self, plugin):
        # Mesuré : 52 patterns + 12 hérités de 1314 = 64/1408 (méthode publiée
        # dans la PR). L'égalité attrape les deux régressions : l'héritage
        # retiré (52) et l'héritage sans restriction de preuve (560).
        assert len(plugin._family_mapping_cache) == 64, len(
            plugin._family_mapping_cache
        )


class TestUnclassifiedCarried:
    """Une détection sans famille est portée dans le résultat, pas droppée."""

    async def test_get_family_statistics_reports_unclassified(self, plugin):
        fallacies = [
            {"family": "diversion_attack", "confidence": 0.8},
            {
                "family": None,
                "confidence": 0.9,
                "name": "Sophisme de Tricherie sans famille EN",
                "taxonomy_key": 922,
            },
        ]
        stats = await plugin.get_family_statistics(fallacies)

        assert stats["diversion_attack"]["count"] == 1  # contrôle : rien de perdu
        unclassified = stats["unclassified"]
        assert unclassified["count"] == 1, stats.keys()
        assert unclassified["names"] == ["Sophisme de Tricherie sans famille EN"]
        assert unclassified["taxonomy_keys"] == [922]
        assert unclassified["present"] is True

    async def test_analyze_comprehensive_carries_unclassified(
        self, plugin, monkeypatch
    ):
        detected = [
            {
                "taxonomy_key": DIVERSION_PK,
                "name": "Diversion",
                "nom_vulgarise": "Diversion",
                "family": "diversion_attack",
                "confidence": 0.8,
                "description": "détournement",
                "severity": "Moyenne",
                "context_relevance": 0.2,
                "family_pattern_score": 0.5,
                "detection_method": "taxonomy_family_diversion_attack",
            },
            {
                "taxonomy_key": 922,
                "name": "Tricherie",
                "nom_vulgarise": "Tricherie",
                "family": None,
                "confidence": 0.9,
                "description": "tricherie",
                "severity": "Indéterminée",
                "context_relevance": 0.0,
                "family_pattern_score": 0.0,
                "detection_method": "taxonomy_unclassified",
            },
        ]
        monkeypatch.setattr(
            plugin, "detect_and_classify", AsyncMock(return_value=detected)
        )
        verifier = AsyncMock()
        verifier.verify_claims = AsyncMock(return_value=[])
        analyzer = FallacyFamilyAnalyzer(
            taxonomy_plugin=plugin, verification_plugin=verifier
        )

        result = await analyzer.analyze_comprehensive(
            "Un texte.", depth=AnalysisDepth.BASIC
        )

        unclassified = result.overall_assessment["unclassified_detections"]
        assert unclassified["count"] == 1, result.overall_assessment.keys()
        assert unclassified["taxonomy_keys"] == [922]
        assert unclassified["names"] == ["Tricherie"]
        # contrôle : la détection mappée reste dans sa famille
        diversion = result.family_results.get(FallacyFamily.DIVERSION_ATTACK)
        assert diversion is not None, result.family_results.keys()
        assert any(
            f["taxonomy_key"] == DIVERSION_PK for f in diversion.fallacies_detected
        )
