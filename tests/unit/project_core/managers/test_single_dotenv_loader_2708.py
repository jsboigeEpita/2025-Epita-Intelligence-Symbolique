"""Production packages load .env through EnvironmentManager, not local walkers."""

import ast
from pathlib import Path

import pytest

from tests.support.tree_walk import iter_files

ROOT = Path(__file__).resolve().parents[4]
PRODUCTION_ROOTS = (
    ROOT / "argumentation_analysis",
    ROOT / "api",
    ROOT / "project_core",
)
LOADER = ROOT / "argumentation_analysis" / "config" / "env_loader.py"


def _dotenv_sites(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = (
                func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            )
            if name == "find_dotenv":
                yield node.lineno, name
            if (
                name == "load_dotenv"
                and not node.args
                and not any(kw.arg == "dotenv_path" for kw in node.keywords)
            ):
                yield node.lineno, "load_dotenv()"
            if name == "SettingsConfigDict":
                for keyword in node.keywords:
                    if keyword.arg == "env_file" and not (
                        isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is None
                    ):
                        yield node.lineno, "SettingsConfigDict(env_file=...)"


def test_production_dotenv_has_one_loader():
    offenders = []
    for root in PRODUCTION_ROOTS:
        for path in iter_files(root, skip_prefixes=("_probe_", "node_modules")):
            if path == LOADER or "_archives" in path.parts:
                continue
            for line, call in _dotenv_sites(path):
                offenders.append(f"{path.relative_to(ROOT)}:{line}: {call}")
    assert (
        not offenders
    ), "Direct .env loaders outside EnvironmentManager:\n" + "\n".join(
        sorted(offenders)
    )


@pytest.mark.parametrize(
    ("call", "rejected"),
    [
        ("load_dotenv()", True),
        ("dotenv.find_dotenv()", True),
        ("find_dotenv(usecwd=True)", True),
        ("load_dotenv(Path('.env'))", False),
        ("load_dotenv(dotenv_path=ROOT / '.env')", False),
        ("SettingsConfigDict(env_file='.env')", True),
        ("SettingsConfigDict(env_prefix='OPENAI_')", False),
    ],
)
def test_guard_classifies_new_loader(tmp_path, call, rejected):
    path = tmp_path / "new_loader.py"
    path.write_text(call, encoding="utf-8")
    assert bool(list(_dotenv_sites(path))) is rejected
