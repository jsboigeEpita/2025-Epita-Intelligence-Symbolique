"""
Garde du shim `agents/extract/` (#2122).

Le shim est un alias de module vers `agents.core.extract.extract_agent`. Il
exposait cet alias sous **deux** formes sur trois : `import ...extract.extract_agent`
et `from ...extract import extract_agent` touchaient le module canonique via
`sys.modules`, mais `getattr(pkg, "extract_agent")` levait AttributeError — la
seule entrée `sys.modules` ne pose pas d'attribut sur le package, c'est le
machinery d'import qui le fait. Ce test épingle les trois formes.

Il épingle aussi la **disparition d'une surface fausse** : `setup_extract_agent`
n'a jamais existé (aucune définition dans le dépôt) et pourtant quatre fichiers
de documentation l'exposaient comme API appelable. Le test refuse son retour
**dans un bloc de code** — là où un lecteur y voit une API. La prose qui raconte
que le symbole n'a jamais existé est de la documentation, pas une surface
fausse : elle reste permise, sinon la garde interdirait d'expliquer le défaut.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]

# Les quatre surfaces documentaires qui présentaient la fausse API (#2122).
DOC_SURFACES = (
    "argumentation_analysis/agents/extract/README.md",
    "argumentation_analysis/agents/core/extract/README.md",
    "argumentation_analysis/agents/docs/exemples_utilisation.md",
    "docs/reference/agents/extract_agent_api.md",
)

PHANTOM = "setup_extract_agent"

CORE_MODULE = "argumentation_analysis.agents.core.extract.extract_agent"


def _phantom_lines_in_code_blocks(path: Path) -> list[int]:
    """Numéros des lignes où le fantôme apparaît **dans un bloc de code**.

    Un exemple de code est ce qui fait croire à une API existante ; une phrase
    qui raconte son absence ne l'est pas. On ne surveille donc que l'intérieur
    des clôtures ```.
    """
    hits: list[int] = []
    inside = False
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            inside = not inside
            continue
        if inside and PHANTOM in line:
            hits.append(lineno)
    return hits


class TestShimAliasAgrees:
    """Les trois formes d'accès à l'alias rendent le même module."""

    def test_package_attribute_is_the_core_module(self) -> None:
        import argumentation_analysis.agents.extract as pkg

        assert getattr(pkg, "extract_agent", None) is not None, (
            "pkg.extract_agent manquant : `sys.modules` seul ne pose pas "
            "l'attribut sur le package (#2122)"
        )
        assert pkg.extract_agent.__name__ == CORE_MODULE

    def test_import_statement_form(self) -> None:
        import argumentation_analysis.agents.extract.extract_agent as via_import

        assert via_import.__name__ == CORE_MODULE

    def test_from_import_form(self) -> None:
        from argumentation_analysis.agents.extract import extract_agent as via_from

        assert via_from.__name__ == CORE_MODULE

    def test_three_forms_are_one_object(self) -> None:
        import argumentation_analysis.agents.extract as pkg
        import argumentation_analysis.agents.extract.extract_agent as via_import
        from argumentation_analysis.agents.extract import extract_agent as via_from

        assert via_import is via_from is pkg.extract_agent

    def test_shim_reexports_the_agent_class(self) -> None:
        from argumentation_analysis.agents.core.extract import ExtractAgent as core
        from argumentation_analysis.agents.extract import ExtractAgent

        assert ExtractAgent is core


class TestPhantomStaysGone:
    """Contrôle négatif : le symbole fantôme n'existe nulle part."""

    def test_package_does_not_expose_the_phantom(self) -> None:
        import argumentation_analysis.agents.extract as pkg

        assert not hasattr(pkg, PHANTOM)

    def test_no_doc_surface_presents_the_phantom(self) -> None:
        offenders = [
            f"{relative}:{lineno}"
            for relative in DOC_SURFACES
            if (REPO_ROOT / relative).is_file()
            for lineno in _phantom_lines_in_code_blocks(REPO_ROOT / relative)
        ]
        assert (
            not offenders
        ), f"{PHANTOM} réapparu comme API dans un bloc de code : {offenders}"


@pytest.mark.parametrize("relative", DOC_SURFACES)
def test_doc_surfaces_exist(relative: str) -> None:
    """Les quatre surfaces surveillées existent encore (sinon la garde dort)."""
    assert (REPO_ROOT / relative).is_file()
