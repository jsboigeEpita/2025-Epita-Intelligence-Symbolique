# tests/unit/argumentation_analysis/reporting/test_one_report_template_2143.py
"""Un seul `UnifiedReportTemplate`, un seul `ReportMetadata` dans ce paquet.

Deux classes homonymes aux mêmes champs laissent deux réponses à « laquelle
j'importe ? », et `is` les distingue à tort. Ce test **re-dérive la partition**
depuis l'arbre syntaxique du paquet : il rougit quand une seconde définition
apparaît, pas quand le paquet grandit.
"""

import ast
from pathlib import Path

import argumentation_analysis.reporting as reporting_pkg
from argumentation_analysis.reporting import document_assembler, models

REPORTING_DIR = Path(reporting_pkg.__file__).resolve().parent
TEMPLATE_CLASS = "UnifiedReportTemplate"
METADATA_CLASS = "ReportMetadata"


def _definers(class_name: str) -> dict:
    """{nom de module: ligne} des modules qui définissent `class_name` à plat."""
    found = {}
    for path in sorted(REPORTING_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                found[path.name] = node.lineno
    return found


def test_scan_is_not_blind():
    """Contrôles d'instrument — un zéro n'est une mesure que s'il peut être non-zéro."""
    assert list(REPORTING_DIR.glob("*.py")), "le paquet ne contient aucun module"
    assert _definers(
        "ReportConfiguration"
    ), "contrôle positif échoué : le balayage AST ne voit pas une classe qui existe"
    assert not _definers(
        "UnifiedReportTemplateThatNeverExisted"
    ), "contrôle négatif échoué : le balayage trouve une classe inventée"


def test_single_template_definition():
    found = _definers(TEMPLATE_CLASS)
    assert set(found) == {"document_assembler.py"}, (
        f"{TEMPLATE_CLASS} doit être défini une seule fois, dans "
        f"document_assembler.py ; définitions trouvées : {found}"
    )


def test_metadata_is_the_canonical_model():
    assert document_assembler.ReportMetadata is models.ReportMetadata


def test_document_assembler_defines_no_local_metadata():
    assert METADATA_CLASS not in _definers(METADATA_CLASS).get(
        "document_assembler.py", ""
    ), "document_assembler redéfinit localement le modèle canonique"
    assert _definers(METADATA_CLASS).get(
        "models.py"
    ), "le modèle canonique doit rester défini dans models.py"
