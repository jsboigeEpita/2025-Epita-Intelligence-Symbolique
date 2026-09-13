"""#2190 — born-red guard: an empty taxonomy cell must not match as "nan".

Measured on the vendored taxonomy (`argumentum_fallacies_taxonomy.csv`,
1408 rows): `nom_vulgarisé` is NaN on **1368** rows — only 40 are named, and
the CSV has no `Name` column at all. `str(nan)` is the truthy string `"nan"`,
so the lexical matcher («`nom_vulgarise and nom_vulgarise in text_lower`»)
adds 0.7 confidence to every empty-named row as soon as the text contains
`nan` **anywhere, including inside a word** — «fi*nan*ce», «mainte*nan*t»,
«gag*nan*ts». Each of the 1368 rows then clears the 0.3 threshold: a probe
text of plain French returned 20 detections at 0.8, all `nom_vulgarise: nan`.

The detector's own constructor is broken on **main** for an unrelated reason
(`InformalAnalysisPlugin` requires a `kernel`; repaired by #2189, open at the
time of writing), so this guard builds the detector around that constructor
and runs the REAL taxonomy through the REAL matching code — the data, the
matcher and the plugin are production objects; only the broken constructor is
bypassed, and this file stays measurable independently of #2189's merge
order.
"""

import logging

import pandas as pd
import pytest
from semantic_kernel import Kernel

from argumentation_analysis.agents.core.informal.informal_definitions import (
    InformalAnalysisPlugin,
)
from argumentation_analysis.agents.core.informal.taxonomy_sophism_detector import (
    TaxonomySophismDetector,
)


@pytest.fixture(scope="module")
def detector() -> TaxonomySophismDetector:
    """The real detector over the real taxonomy (see module docstring)."""
    det = TaxonomySophismDetector.__new__(TaxonomySophismDetector)
    det.logger = logging.getLogger("TaxonomySophismDetector")
    det.plugin = InformalAnalysisPlugin(kernel=Kernel(), taxonomy_file_path=None)
    det._taxonomy_cache = None
    return det


def _is_nan_like(value) -> bool:
    return not isinstance(value, str) and (value is None or pd.isna(value))


# Plain French texts whose ONLY overlap with the taxonomy is the substring
# "nan" inside a word. Each must detect nothing.
INNOCENT_TEXTS = [
    "La finance mondiale est un sujet complexe.",
    "Les enfants gagnants sont maintenant a table.",
    "Ce raisonnement est interessant a analyser.",  # aucun "nan" : temoin negatif du declencheur
]


class TestEmptyCellsCannotMatch:
    def test_trigger_is_really_the_nan_substring(self):
        """Non-vacuity of the reproduction: two probes contain "nan", one does not."""
        assert "nan" in INNOCENT_TEXTS[0].lower()
        assert "nan" in INNOCENT_TEXTS[1].lower()
        assert "nan" not in INNOCENT_TEXTS[2].lower()

    @pytest.mark.parametrize("text", INNOCENT_TEXTS)
    def test_text_without_fallacy_name_detects_nothing(self, detector, text):
        """The population of empty-named rows must not be returned as detections."""
        detected = detector.detect_sophisms_from_taxonomy(text, 20)
        assert detected == [], (
            f"{len(detected)} detection(s) on a text that names no fallacy — "
            f"first: {[(d['taxonomy_key'], d['nom_vulgarise']) for d in detected[:3]]}"
        )

    def test_no_detection_carries_a_nan_name(self, detector):
        """NaN must not ride into the detected dicts (it broke the ClassifiedFallacy
        validation downstream: `Input should be a valid string`)."""
        detected = detector.detect_sophisms_from_taxonomy(
            "La finance mondiale est un sujet complexe.", 20
        )
        bad = [d for d in detected if _is_nan_like(d.get("nom_vulgarise"))]
        assert bad == [], f"detections carrying NaN: {bad[:3]}"

    def test_search_pattern_cannot_match_empty_named_rows(self, detector):
        """Same defect in the search direction: `pattern in nom_vulgarise` with
        nom_vulgarise == "nan" scored every empty-named row 0.8."""
        hits = detector.search_sophisms_by_pattern("an", 20)
        bad = [h for h in hits if _is_nan_like(h.get("nom_vulgarise"))]
        assert bad == [], (
            f"{len(bad)} hit(s) on empty-named rows — first: "
            f"{[(h['taxonomy_key'], h['nom_vulgarise']) for h in bad[:3]]}"
        )

    def test_main_branches_carry_string_names(self, detector):
        """`get_main_branches` echoed the raw cell: all 8 roots carried NaN."""
        branches = detector.get_main_branches()
        bad = [b for b in branches if _is_nan_like(b.get("nom_vulgarise"))]
        assert len(branches) > 0, "instrument: la taxonomie doit rendre des branches"
        assert bad == [], f"branches carrying NaN: {[b['taxonomy_key'] for b in bad]}"

    def test_siblings_carry_string_names(self, detector):
        """`_get_parent_context` echoed the raw cell into `related_sophisms`."""
        context = detector._get_parent_context(5)
        siblings = context.get("siblings", [])
        bad = [s for s in siblings if _is_nan_like(s.get("nom_vulgarise"))]
        assert bad == [], f"siblings carrying NaN: {[s['taxonomy_key'] for s in bad]}"


class TestNamedRowsStillMatch:
    """Anti-'empty the guard': the fix must not disable the matching it guards."""

    def test_a_named_row_is_still_detected(self, detector):
        df = detector._get_taxonomy_df()
        named = df[df["nom_vulgarisé"].notna()]
        assert len(named) > 0, "instrument: la taxonomie doit porter des lignes nommees"
        pk = int(named.index[0])
        name = str(df.loc[pk, "nom_vulgarisé"])

        detected = detector.detect_sophisms_from_taxonomy(
            f"Le texte mentionne {name} de maniere explicite.", 20
        )
        hits = [d for d in detected if d["taxonomy_key"] == pk]
        assert hits, (
            f"la ligne nommee {pk} ({name!r}) doit rester detectable, "
            f"obtenu {[(d['taxonomy_key'], d['nom_vulgarise']) for d in detected[:5]]}"
        )
        assert hits[0]["nom_vulgarise"] == name
