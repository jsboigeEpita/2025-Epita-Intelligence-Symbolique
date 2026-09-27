"""#2707: a checkout without its root .env loads no .env at all.

``EnvironmentManager`` used to fall back on ``dotenv.find_dotenv()`` when the
root .env was absent. ``find_dotenv()`` walks up from the module's directory,
past the checkout, and returns the first .env it meets. ``project_core`` only
lives inside the repository, so inside the checkout there was nothing left for
it to find: the fallback could only load a file from outside. Measured on
ai-01: a worktree under ``D:\\`` loaded 19 keys of another project's .env,
among them a Hugging Face token, ``OMP_NUM_THREADS`` and ``TZ``.

The witness emulates that walk: ``find_dotenv`` answers with a .env placed
above a repository root that has none, as the real walk does on such a seat.
The real walk cannot be pointed at ``tmp_path``: it starts from the module's
own file. The fallback is gone, so the answer must reach nothing: no variable
of that file enters the process, and no upward search is attempted.
"""

import os
from pathlib import Path
from unittest.mock import patch

import dotenv

import argumentation_analysis.config.env_loader as _em_mod
from project_core.managers.environment_manager import EnvironmentManager

_FOREIGN_KEY = "DOTENV_2707_FOREIGN_KEY"


def _repo_without_env_under_a_foreign_env(tmp_path: Path) -> Path:
    (tmp_path / ".env").write_text(f'{_FOREIGN_KEY}="foreign"\n', encoding="utf-8")
    repo = tmp_path / "checkout"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    return repo


def test_a_checkout_without_its_env_loads_nothing_from_above(tmp_path: Path) -> None:
    repo = _repo_without_env_under_a_foreign_env(tmp_path)
    foreign = str(tmp_path / ".env")

    with patch.dict(os.environ, {}, clear=False), patch.object(
        _em_mod, "_find_repo_root", return_value=repo
    ), patch.object(dotenv, "find_dotenv", return_value=foreign) as walk:
        os.environ.pop(_FOREIGN_KEY, None)
        manager = EnvironmentManager()
        leaked = os.environ.get(_FOREIGN_KEY)

    assert leaked is None, f"a .env above the checkout was loaded: {foreign}"
    assert manager.dotenv_path == ""
    assert manager.dotenv_loaded is False
    assert walk.call_count == 0, "EnvironmentManager searched above the checkout"


def test_the_root_env_is_still_the_one_loaded(tmp_path: Path) -> None:
    """The control: the same layout with a root .env loads the root .env only."""
    repo = _repo_without_env_under_a_foreign_env(tmp_path)
    (repo / ".env").write_text('DOTENV_2707_ROOT_KEY="root"\n', encoding="utf-8")

    with patch.dict(os.environ, {}, clear=False), patch.object(
        _em_mod, "_find_repo_root", return_value=repo
    ):
        os.environ.pop(_FOREIGN_KEY, None)
        os.environ.pop("DOTENV_2707_ROOT_KEY", None)
        manager = EnvironmentManager()
        root_value = os.environ.get("DOTENV_2707_ROOT_KEY")
        leaked = os.environ.get(_FOREIGN_KEY)

    assert manager.dotenv_path == str(repo / ".env")
    assert manager.dotenv_loaded is True
    assert root_value == "root"
    assert leaked is None
