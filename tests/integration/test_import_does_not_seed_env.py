"""Contrôle #1794/#1817/#1827 : aucun module test_*.py ne sème os.environ à l'import.

Toute bande qui collecte un répertoire importe chacun de ses ``test_*.py`` ;
un ``load_dotenv()`` au niveau module (ou une écriture ``os.environ[...] =``)
exécuté à ce moment charge le ``.env`` local dans l'environnement du process
pour toute la session pytest — la clé réelle devient lisible par chaque test
qui suit, et un run local cesse d'être reproductible face à la CI (#1827).

La population n'est PAS codée en dur : elle est DÉCOUVERTE par un balayage
AST de ``tests/**/test_*.py`` (hors ``_archived``). Un futur semeur fait donc
rougir ce garde sans édition — c'était le défaut du garde #1824, qui ne
voyait que sa victime canonique (``test_authenticite_finale_gpt4o.py``,
corrigée en #1824).

Le balayage considère « niveau module » tout ce qui s'exécute à l'import :
le corps du module **plus** les corps des ``if`` / ``try`` / ``with`` /
``for`` / ``while`` de niveau module, récursivement — et **jamais**
l'intérieur d'un ``def`` / ``class`` (le point d'entrée ``main()`` d'un
script a le droit d'appeler ``load_dotenv()`` : c'est le correctif #1824
lui-même, le témoin négatif du garde).

#1827 (leçon ai-01) : le texte est lu en ``utf-8-sig`` — 8 fichiers du dépôt
portent un BOM UTF-8 qu'``ast.parse`` refuse après un ``read_text(utf-8)``
nu ; ces fichiers étaient silencieusement hors population et le balayage
rendait un faux zéro d'allure honnête. Le garde compte ses échecs de
parsing et ROUGIT si ce compte n'est pas nul.
"""

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = REPO_ROOT / "tests"

# Motifs recherchés au niveau module : appel load_dotenv (nom simple ou
# qualifié — ``dotenv.load_dotenv()``), et mutations directes d'os.environ
# (assignation d'item, setdefault, update). La DoD #1827 cite ces formes.
_SEED_CALL_NAMES = {"load_dotenv"}
_ENVIRON_MUTATING_METHODS = {"setdefault", "update"}
_ASSIGN_TARGETS = {"environ"}


def _is_load_dotenv_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in _SEED_CALL_NAMES
    if isinstance(func, ast.Attribute):
        return func.attr in _SEED_CALL_NAMES
    return False


def _is_environ_mutation(node: ast.AST) -> bool:
    # os.environ[...] = ...  (Assign/AnnAssign/AugAssign target Subscript)
    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        targets = node.targets if hasattr(node, "targets") else [node.target]
        for target in targets:
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Attribute)
                and target.value.attr in _ASSIGN_TARGETS
                and isinstance(target.value.value, ast.Name)
                and target.value.value.id == "os"
            ):
                return True
        return False
    # os.environ.setdefault(...) / os.environ.update(...)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr in _ENVIRON_MUTATING_METHODS:
            recv = node.func.value
            if (
                isinstance(recv, ast.Attribute)
                and recv.attr in _ASSIGN_TARGETS
                and isinstance(recv.value, ast.Name)
                and recv.value.id == "os"
            ):
                return True
    return False


def _iter_module_level_nodes(tree: ast.Module):
    """Yield every node that EXECUTES at import time.

    Walks the module body and descends into statement blocks of level-module
    control flow (if/try/with/for/while), recursively — but never into
    function/class bodies: those run at call time, not import time.
    """
    stack = list(ast.iter_child_nodes(tree))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        stack.extend(ast.iter_child_nodes(node))


def _seed_evidence(path: Path) -> str:
    """Return '<motif> ligne N' if this module seeds env at import, else ''."""
    text = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)
    for node in _iter_module_level_nodes(tree):
        if _is_load_dotenv_call(node):
            return f"load_dotenv() (ligne {node.lineno})"
        if _is_environ_mutation(node):
            kind = getattr(node, "func", None)
            what = (
                f"os.environ.{kind.attr}(...)"
                if kind is not None
                else "os.environ[...] ="
            )
            return f"{what} (ligne {node.lineno})"
    return ""


def _iter_test_files():
    for path in sorted(TESTS_ROOT.rglob("test_*.py")):
        if "_archived" in path.parts:
            continue
        yield path


def _parse_failures() -> list:
    failures = []
    for path in _iter_test_files():
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"))
        except SyntaxError as exc:
            failures.append(f"{path.relative_to(REPO_ROOT)}: {exc}")
    return failures


def discover_seeders() -> list:
    """All test_*.py modules that seed os.environ at import time."""
    seeders = []
    for path in _iter_test_files():
        evidence = _seed_evidence(path)
        if evidence:
            seeders.append(f"{path.relative_to(REPO_ROOT)}: {evidence}")
    return seeders


# La sonde vit dans un subprocess à environnement MINIMAL : le process pytest
# a typiquement déjà chargé le .env (conftest --allow-dotenv) et un subprocess
# héritier repartirait d'un os.environ déjà saturé — la fuite serait
# invisible. Env réduit au strict nécessaire Windows + cwd = racine du dépôt
# pour que l'éventuel load_dotenv() du semeur trouve le vrai .env — c'est le
# chemin de la fuite. Seuls les NOMS de clés remontent, jamais les valeurs.
_PROBE = """
import importlib.util, json, os
before = dict(os.environ)
spec = importlib.util.spec_from_file_location("seed_probe", {victim!r})
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
after = dict(os.environ)
gained = sorted(k for k in after if before.get(k) != after[k])
print("GAINED:" + json.dumps(gained))
"""

_CHILD_ENV = {
    k: os.environ[k]
    for k in ("SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP", "COMSPEC")
    if k in os.environ
}


def _probe_import_gains(victim: Path) -> list:
    result = subprocess.run(
        [sys.executable, "-c", _PROBE.format(victim=str(victim))],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=_CHILD_ENV,
        timeout=120,
    )
    marker = next(
        (line for line in result.stdout.splitlines() if line.startswith("GAINED:")),
        None,
    )
    assert marker is not None, (
        "la sonde n'a pas rendu son bilan — "
        f"returncode={result.returncode} "
        f"stdout={result.stdout[-500:]!r} stderr={result.stderr[-500:]!r}"
    )
    return json.loads(marker[len("GAINED:") :])


def test_ast_sweep_parses_every_test_file():
    """Un balayage qui saute des fichiers en silence rend un faux zéro.

    8 fichiers du dépôt portent un BOM UTF-8 ; lus en utf-8 nu ils échouent
    ast.parse et étaient hors population. Le garde compte ses échecs et
    rougit si un seul lui échappe (#1827).
    """
    failures = _parse_failures()
    assert failures == [], (
        f"le balayage AST n'a pas pu parser {len(failures)} fichier(s) — ils "
        f"sont hors population (faux zéro possible) : {failures}"
    )


def test_no_test_module_seeds_env_at_import():
    """Le garde vivant : la population de semeurs au niveau module est vide.

    Rouge dès qu'un test_*.py appelle load_dotenv / mute os.environ au niveau
    module — SANS édition : la population est découverte, pas codée en dur.
    """
    seeders = discover_seeders()
    assert seeders == [], (
        f"module(s) test_*.py qui sèment os.environ à l'import (#1794/#1817/"
        f"#1827) : {seeders} — le chargement d'env appartient aux points "
        "d'entrée (main()) ou au conftest (--allow-dotenv), jamais à l'import "
        "d'un module de test"
    )


def test_discovered_seeders_do_not_seed_os_environ():
    """Preuve dynamique par import NU (subprocess à env minimal).

    Tourne sur la population découverte ; population vide aujourd'hui, ce
    test est alors trivialement vert — le verdict de garde vit dans le test
    statique ci-dessus. Si un semeur apparaît, il est importé ici à env
    minimal et sa fuite réelle est listée (noms de clés uniquement).
    """
    for seeder in discover_seeders():
        rel = seeder.split(":")[0]
        gained = _probe_import_gains(REPO_ROOT / rel)
        assert gained == [], (
            f"l'import de {rel} a semé os.environ : {gained} — {seeder} "
            "(#1794/#1817/#1827)"
        )
