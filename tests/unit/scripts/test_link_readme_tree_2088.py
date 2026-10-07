# -*- coding: utf-8 -*-
"""#2962 rework — le producteur de liens n'écrit jamais dans une fence ouverte.

Revue coord R1072 : ``argumentation_analysis/pipelines/README.md`` portait
la seule fence mermaid jamais fermée de l'arbre ; le producteur y a appendu
« ## Enfants documentés » + le lien enfant, et la section a rendu DANS le
bloc de code — la page rendue ne liait rien alors que la garde (regex sur
texte brut) comptait le lien.

Né-rouge sur la tête initiale de la PR : ``_add_child_list`` appendait dans
la fence ouverte (le témoin de fermeture redden).
"""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_PRODUCER = REPO_ROOT / "scripts" / "docs" / "link_readme_tree_2088.py"


def _load_producer():
    spec = importlib.util.spec_from_file_location("link_readme_tree_2088", _PRODUCER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestProducerNeverAppendsIntoAnOpenFence:
    def test_child_list_closes_the_open_fence_first(self):
        """La forme mesurée : fence jamais fermée en fin de fichier. Le
        producteur la FERME avant d'appendre — la section rend hors du bloc
        et le lien existe pour le lecteur."""
        p = _load_producer()
        text = "# Fiche\n\n```mermaid\ngraph TD\n    D --> E[Sortie];"
        out = p._add_child_list(text, "\n", ["child"])
        assert "```\n\n## Enfants documentés" in out
        assert p._rendered_md_link_targets(out) == {"./child/README.md"}

    def test_closed_fence_is_left_alone(self):
        p = _load_producer()
        text = "# Fiche\n\n```\nexemple\n```\n"
        out = p._add_child_list(text, "\n", ["child"])
        assert out.count("```") == 2  # aucune fence ajoutée ni retirée

    def test_ends_in_open_fence_detection(self):
        """Règles CommonMark : même caractère, longueur ≥, aucun texte
        après le marqueur de fermeture."""
        p = _load_producer()
        assert p._ends_in_open_fence("```mermaid\nA\n", "\n")
        assert not p._ends_in_open_fence("```mermaid\nA\n```\n", "\n")
        # une fence plus courte ne ferme pas une plus longue
        assert p._ends_in_open_fence("````\nA\n```\n", "\n")
        # un backtick triple ne ferme pas une fence tilde
        assert not p._ends_in_open_fence("~~~\nA\n~~~\n", "\n")
        assert p._ends_in_open_fence("~~~\n```\n", "\n")

    def test_producer_counts_rendered_links_only(self):
        """Le producteur décide des manquants sur les liens RENDUS, pas sur
        le texte brut — sinon il croit le parent déjà lié par un lien écrit
        dans un bloc de code."""
        p = _load_producer()
        fenced = "# T\n\n```\n[`c/`](./c/README.md)\n```\n"
        assert p._rendered_md_link_targets(fenced) == set()
