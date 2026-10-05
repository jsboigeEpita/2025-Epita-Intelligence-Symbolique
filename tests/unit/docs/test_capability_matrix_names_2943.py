# -*- coding: utf-8 -*-
"""#2943: chaque nom CamelCase de la colonne Component de la matrice de
capacités résout vers une définition de production.

``docs/architecture/spectacular_capability_matrix.md`` se présente comme
l'audit courant des composants (« Audit of all accumulated components »),
mais #2940/#2943 y ont mesuré 3 noms morts (``FactExtractionAgent``,
``SynthesisAgent``, ``RhetoricalResultAnalyzer``). La garde de citations
#2669 ne les a pas vus : elle lit des noms en backticks, et la colonne
Component est en texte nu. La garde, c'est le census lui-même.

Population couverte (déclarée) : les 6 tables numérotées du document —
Agents, Semantic Kernel Plugins, Tweety Extensions & Semantics, External
Solvers, Workflows, Services & Infrastructure — soit les 72 lignes
numérotées ; les entrées de la colonne Component qui sont un jeton
CamelCase unique. Mesuré à la naissance : 43 noms.

Résolution : chaque nom doit être une **définition** (``ClassDef``,
``FunctionDef``, ``AsyncFunctionDef`` ou ``Assign`` de module) dans un
``.py`` de production listé par ``git ls-files`` sous
``argumentation_analysis/``. Un jeton exact dans une docstring ne suffit
pas (leçon #2669 : une mention n'est pas un appel). Lecture en
``utf-8-sig`` : au moins un fichier de production porte un BOM et
``ast.parse`` le rejette en ``utf-8`` nu (silencieux si avalé — mesuré sur
``fol_logic_agent.py``).

Pas de marche récursive : la liste des fichiers vient de ``git ls-files``
seulement (garde #2607).
"""

import ast
import re
import subprocess
from functools import lru_cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MATRIX = REPO / "docs" / "architecture" / "spectacular_capability_matrix.md"

# Les 6 tables numérotées que couvre le census. Une disparition = une
# population qui rétrécit en silence : la garde le voit.
EXPECTED_TABLES = (
    "Agents (15)",
    "Semantic Kernel Plugins (20)",
    "Tweety Extensions & Semantics (11)",
    "External Solvers (4)",
    "Workflows (12)",
    "Services & Infrastructure (10)",
)
# Planchers, juste sous le compte mesuré à la naissance (72 lignes,
# 43 noms) : la matrice peut grandir, pas fondre.
MIN_NUMBERED_ROWS = 70
MIN_NAMES = 40

CAMEL_CASE = re.compile(r"^[A-Z][A-Za-z0-9_]*$")

# Noms cités à dessein qui ne sont PAS des symboles Python. Chaque entrée
# doit rester réellement citée et réellement absente des définitions (une
# entrée morte ou vivante redden — même discipline que ABSENT_BY_DESIGN
# de #2669).
EXCEPTIONS = {
    "GovernanceAgent": (
        "clé de chaîne d'agent conversationnel (phase_scoped_state.py), "
        "pas une classe — la capability passe par GovernancePlugin (ligne 25)"
    ),
    "EProver": "solveur externe (binaire), pas un symbole Python",
    "Prover9": "solveur externe (binaire), pas un symbole Python",
    "SPASS": "solveur externe (binaire, via SPASSMlReasoner), pas un symbole Python",
}


@lru_cache(maxsize=1)
def _numbered_rows() -> tuple[tuple[str, str], ...]:
    """(titre de table, cellule Component) pour chaque ligne numérotée."""
    rows: list[tuple[str, str]] = []
    table = ""
    for line in MATRIX.read_text(encoding="utf-8-sig").splitlines():
        header = re.match(r"^## (.+)$", line)
        if header:
            table = header.group(1)
            continue
        if not (line.startswith("| ") and line.count("|") >= 5):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells[0].isdigit():
            rows.append((table, cells[1]))
    return tuple(rows)


def _component_names() -> list[str]:
    return [c for _, c in _numbered_rows() if CAMEL_CASE.match(c)]


@lru_cache(maxsize=1)
def _production_defs() -> frozenset[str]:
    """Noms définis dans les .py de production (git ls-files, aucun walk)."""
    listed = subprocess.run(
        ["git", "ls-files", "argumentation_analysis/"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    defs: set[str] = set()
    for path in listed:
        if not path.endswith(".py"):
            continue
        try:
            tree = ast.parse((REPO / path).read_text(encoding="utf-8-sig"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                defs.add(node.name)
        for node in tree.body:  # Assign de module uniquement
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defs.add(target.id)
    return frozenset(defs)


def test_population_couverte_ne_fond_pas():
    """Les 6 tables numérotées existent, et les planchers tiennent."""
    tables = {table for table, _ in _numbered_rows()}
    missing = [t for t in EXPECTED_TABLES if t not in tables]
    assert not missing, f"tables disparues de la matrice : {missing}"
    assert len(_numbered_rows()) >= MIN_NUMBERED_ROWS, (
        f"{len(_numbered_rows())} lignes numérotées < {MIN_NUMBERED_ROWS} : "
        "la population du census a fondu, réviser la garde"
    )
    assert len(_component_names()) >= MIN_NAMES, (
        f"{len(_component_names())} noms CamelCase < {MIN_NAMES} : "
        "la population du census a fondu, réviser la garde"
    )


def test_chaque_nom_resout_vers_une_definition():
    """Contrôle principal : nom cité ⇒ définition vivante (ou exception)."""
    defs = _production_defs()
    dead = [
        name
        for name in _component_names()
        if name not in defs and name not in EXCEPTIONS
    ]
    assert not dead, (
        "noms de la colonne Component sans définition de production : "
        f"{dead} — corriger la ligne (le symbole vivant) ou, si le nom est "
        "cité à dessein, l'ajouter à EXCEPTIONS avec sa raison"
    )


def test_les_exceptions_sont_reelles():
    """Une exception doit être citée ET absente — sinon elle abrite un nom
    vivant ou survit à sa citation."""
    cited = set(_component_names())
    defs = _production_defs()
    for name, reason in EXCEPTIONS.items():
        assert name in cited, (
            f"EXCEPTIONS['{name}'] ({reason}) n'est plus citée dans la "
            "matrice — retirer l'entrée"
        )
        assert name not in defs, (
            f"EXCEPTIONS['{name}'] résout désormais vers une définition de "
            "production — retirer l'entrée, la garde doit le couvrir"
        )
