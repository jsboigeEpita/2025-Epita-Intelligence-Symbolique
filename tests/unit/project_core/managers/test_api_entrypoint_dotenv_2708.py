"""API startup loads only the selected checkout's root .env."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_api_entrypoint_loads_root_not_cwd_or_nested(tmp_path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".env").write_text("DOTENV_2708_SOURCE=root\n", encoding="utf-8")
    (tmp_path / ".env").write_text("DOTENV_2708_FOREIGN=foreign\n", encoding="utf-8")
    code = (
        "import os\n"
        "import argumentation_analysis.config.env_loader as manager\n"
        f"manager._find_repo_root = lambda: __import__('pathlib').Path({str(checkout)!r})\n"
        "import api.main\n"
        "print('DOTENV_2708_RESULT=' + repr((os.getenv('DOTENV_2708_SOURCE'), "
        "os.getenv('DOTENV_2708_FOREIGN'))))\n"
    )
    env = os.environ.copy()
    env.pop("DOTENV_2708_SOURCE", None)
    env.pop("DOTENV_2708_FOREIGN", None)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")])
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-3000:]
    assert "DOTENV_2708_RESULT=('root', None)" in result.stdout
