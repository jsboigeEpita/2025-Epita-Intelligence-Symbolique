"""Contrôle #1794/#1817/#1827 : aucun test_*.py ne sème os.environ à l'import.

La population est DÉCOUVERTE, pas codée en dur (#1827) : un balayage AST sur
tous les ``tests/**/test_*.py`` (hors ``_archived``) repère tout code exécutable
au niveau module — corps du module et corps des ``if``/``try``/``with``/``for``
de niveau module, récursivement, jamais l'intérieur d'un ``def``/``class``/``lambda``
— qui appelle ``load_dotenv`` ou écrit dans ``os.environ``. Un futur semeur fait
rougir ce contrôle sans édition.

Trois rouges possibles :
- parsing : un fichier illisible (BOM U+FEFF → lire en ``utf-8-sig``) serait
  silencieusement hors population — faux zéro, le défaut même que ce contrôle
  empêche. Le balayage compte ses échecs et rougit s'il y en a.
- statique : un site semeur est listé (fichier:ligne) ;
- dynamique : chaque semeur découvert est importé dans un subprocess à env
  minimal, qui doit ne rien gagner — preuve d'exécution, pas de lecture.

``conftest.py`` et les points d'entrée applicatifs ont le droit d'appeler
``load_dotenv()`` : la population est strictement ``test_*.py`` au niveau module.
"""

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_ROOT = REPO_ROOT / "tests"


# --- 1. Balayage AST : la population est découverte, jamais codée en dur ---


def _iter_test_files():
    for path in sorted(TESTS_ROOT.rglob("test_*.py")):
        if "_archived" in path.parts:
            continue
        yield path


def _parse(path: Path) -> ast.Module:
    # utf-8-sig : le dépôt porte des fichiers à BOM U+FEFF ; ast.parse lève
    # « invalid non-printable character » sur une lecture en utf-8 nu — les
    # fichiers sautés en silence faussent la population vers le bas.
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def _iter_module_level(stmts):
    """Statements exécutés à l'import : corps du module + corps des
    if/while/for/with/try de niveau module (else/except/finally compris),
    récursivement — jamais l'intérieur d'un def/class (exécuté à l'appel)."""
    for stmt in stmts:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(stmt, (ast.If, ast.While)):
            yield stmt
            yield from _iter_module_level(stmt.body)
            yield from _iter_module_level(stmt.orelse)
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            yield stmt
            yield from _iter_module_level(stmt.body)
            yield from _iter_module_level(stmt.orelse)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            yield stmt
            yield from _iter_module_level(stmt.body)
        elif isinstance(stmt, ast.Try):
            yield stmt
            yield from _iter_module_level(stmt.body)
            for handler in stmt.handlers:
                yield from _iter_module_level(handler.body)
            yield from _iter_module_level(stmt.orelse)
            yield from _iter_module_level(stmt.finalbody)
        else:
            yield stmt


def _is_os_environ(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute):
        return (
            node.attr == "environ"
            and isinstance(node.value, ast.Name)
            and node.value.id == "os"
        )
    return isinstance(node, ast.Name) and node.id == "environ"


def _iter_call_nodes(root: ast.AST):
    """Appels d'une expression, sans descendre dans les lambdas — leur corps
    s'exécute à l'appel, pas à l'import (témoin négatif du balayage)."""
    stack = [root]
    while stack:
        node = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Lambda):
                continue
            if isinstance(child, ast.Call):
                yield child
            stack.append(child)


def _seed_in_stmt(stmt) -> str | None:
    """Motif semeur dans un statement de niveau module, sinon None."""
    # Appels : load_dotenv() simple ou qualifié, os.environ.update/setdefault
    exprs: list[ast.AST]
    if isinstance(stmt, (ast.If, ast.While)):
        exprs = [stmt.test]
    elif isinstance(stmt, (ast.For, ast.AsyncFor)):
        exprs = [stmt.iter]
    elif isinstance(stmt, (ast.With, ast.AsyncWith)):
        exprs = [item.context_expr for item in stmt.items]
    else:
        exprs = [stmt]
    for expr in exprs:
        for node in _iter_call_nodes(expr):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "load_dotenv":
                return "load_dotenv()"
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "load_dotenv"
                and isinstance(func.value, ast.Name)
                and func.value.id == "dotenv"
            ):
                return "dotenv.load_dotenv()"
            if (
                isinstance(func, ast.Attribute)
                and func.attr in ("update", "setdefault")
                and _is_os_environ(func.value)
            ):
                return f"os.environ.{func.attr}(...)"
    # Écritures : os.environ[...] = ...
    targets: list[ast.AST] = []
    if isinstance(stmt, ast.Assign):
        targets = list(stmt.targets)
    elif isinstance(stmt, (ast.AnnAssign, ast.AugAssign)):
        targets = [stmt.target]
    for target in targets:
        if isinstance(target, ast.Subscript) and _is_os_environ(target.value):
            return "os.environ[...] = ..."
    return None


def _parse_failures() -> list[str]:
    failures = []
    for path in _iter_test_files():
        try:
            _parse(path)
        except SyntaxError as exc:
            failures.append(f"{path.relative_to(REPO_ROOT)}: {exc}")
    return failures


def _sowers() -> list[tuple[str, str]]:
    sites = []
    for path in _iter_test_files():
        tree = _parse(path)
        for stmt in _iter_module_level(tree.body):
            kind = _seed_in_stmt(stmt)
            if kind is not None:
                rel = path.relative_to(REPO_ROOT).as_posix()
                sites.append((f"{rel}:{stmt.lineno}", kind))
    return sites


def _sower_paths() -> list[str]:
    paths = []
    for path in _iter_test_files():
        tree = _parse(path)
        if any(
            _seed_in_stmt(stmt) is not None for stmt in _iter_module_level(tree.body)
        ):
            paths.append(path.relative_to(REPO_ROOT).as_posix())
    return paths


# --- 2. La sonde dynamique : import en subprocess à env minimal ---


# La sonde vit dans un subprocess à environnement MINIMAL : le process pytest
# a typiquement déjà chargé le .env (conftest / plugin dotenv), et un
# subprocess héritier repartirait d'un os.environ déjà saturé — la fuite
# serait invisible. Env réduit au strict nécessaire Windows + cwd = racine du
# dépôt pour que l'éventuel load_dotenv() du semeur trouve le vrai .env —
# c'est le chemin de la fuite. Seuls les NOMS de clés remontent, jamais les
# valeurs.
_PROBE = """
import importlib.util, json, os
before = dict(os.environ)
spec = importlib.util.spec_from_file_location("seeded_victim", {victim!r})
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


def test_ast_sweep_parses_every_test_file():
    failures = _parse_failures()
    assert failures == [], (
        "des fichiers test_*.py échouent au parsing — ils seraient hors "
        "population, et le balayage rendrait un faux zéro : "
        f"{failures}"
    )


def test_no_module_level_env_seeder_in_tests():
    sites = _sowers()
    assert sites == [], (
        "des test_*.py sèment os.environ au niveau module — ce code s'exécute "
        "à l'import, chargé par toute bande qui collecte le fichier, et la "
        "clé réelle devient lisible par chaque test qui suit : "
        f"{sites} — déplacer le load_dotenv()/l'écriture dans une fonction "
        "(#1794/#1817/#1827)"
    )


# Boucle sur la population découverte (pas de @pytest.mark.parametrize) :
# une paramétrisation vide collecte un placeholder test[NOTSET] SKIPPED sous
# pytest 8.4.1 — un artefact de collecte, pas un signal. En forme boucle, la
# population propre rend ce test trivialement vert SANS artefact ; dès qu'un
# semeur apparaît, chaque fichier fautif est prouvé à l'exécution. Le rouge
# porteur de sens reste le contrôle statique ci-dessus.
def test_seeder_import_does_not_seed_os_environ():
    for seeder in _sower_paths():
        _assert_import_seeds_nothing(seeder)


def _assert_import_seeds_nothing(seeder):
    victim = REPO_ROOT / seeder
    result = subprocess.run(
        [sys.executable, "-c", _PROBE.format(victim=str(victim))],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=_CHILD_ENV,
        timeout=180,
    )
    marker = next(
        (line for line in result.stdout.splitlines() if line.startswith("GAINED:")),
        None,
    )
    assert marker is not None, (
        f"la sonde n'a pas rendu son bilan pour {seeder} — "
        f"returncode={result.returncode} "
        f"stdout={result.stdout[-500:]!r} stderr={result.stderr[-500:]!r}"
    )
    gained = json.loads(marker[len("GAINED:") :])
    assert gained == [], (
        f"l'import de {seeder} a semé os.environ : {gained} — un load_dotenv() "
        "au niveau module charge le .env local pour toute la session "
        "(#1794/#1817/#1827)"
    )
