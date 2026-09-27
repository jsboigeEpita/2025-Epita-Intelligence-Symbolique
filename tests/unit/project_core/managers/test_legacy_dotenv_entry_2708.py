"""Legacy loader cannot select nested or foreign .env files."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_legacy_loader_import_uses_one_loader(tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".env").write_text("DOTENV_2708_LEGACY=root\n", encoding="utf-8")
    (tmp_path / ".env").write_text("DOTENV_2708_FOREIGN=foreign\n", encoding="utf-8")
    code = (
        "import os\n"
        "import project_core.managers.environment_manager as m\n"
        f"m._find_repo_root = lambda: __import__('pathlib').Path({str(checkout)!r})\n"
        "import project_core.core_from_scripts.load_dotenv\n"
        "print('DOTENV_2708_RESULT=' + repr((os.getenv('DOTENV_2708_LEGACY'), "
        "os.getenv('DOTENV_2708_FOREIGN'))))\n"
    )
    env = os.environ.copy()
    env.pop("DOTENV_2708_LEGACY", None)
    env.pop("DOTENV_2708_FOREIGN", None)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr[-3000:]
    assert "DOTENV_2708_RESULT=('root', None)" in result.stdout


def test_legacy_helper_ignores_nested_and_foreign_start_paths(tmp_path, monkeypatch):
    from project_core.core_from_scripts import load_dotenv as legacy

    checkout = tmp_path / "checkout"
    module_path = checkout / "project_core" / "core_from_scripts" / "load_dotenv.py"
    module_path.parent.mkdir(parents=True)
    monkeypatch.setattr(legacy, "__file__", str(module_path))
    nested = checkout / "nested"
    nested.mkdir()
    (nested / ".env").write_text("NESTED=wrong\n", encoding="utf-8")
    (tmp_path / ".env").write_text("FOREIGN=wrong\n", encoding="utf-8")

    assert legacy.find_dotenv_file(str(nested)) is None
    assert legacy.find_dotenv_file(str(tmp_path)) is None

    root_env = checkout / ".env"
    root_env.write_text("ROOT=right\n", encoding="utf-8")
    assert legacy.find_dotenv_file(str(nested)) == str(root_env)
    assert legacy.find_dotenv_file(str(tmp_path)) == str(root_env)
