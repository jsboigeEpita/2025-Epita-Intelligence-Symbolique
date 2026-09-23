# -*- coding: utf-8 -*-
"""
Manages environment variables for the project.
Loads root .env deterministically: it wins over sub-.env files (#1295) and loses
to the values the caller started the process with, even "" (#2472).
Warns when secondary .env files carry a different OPENAI_API_KEY.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Optional, Union

from dotenv import dotenv_values, load_dotenv

logger = logging.getLogger(__name__)

# The environment the caller started the process with, captured when this module
# is first imported: before EnvironmentManager has loaded any .env (#2472).
# tests/conftest.py imports this module first thing, so a pytest session captures
# the command line's environment.
_CALLER_ENVIRONMENT: Dict[str, str] = dict(os.environ)

# Secondary .env paths relative to repo root — parsed for divergence detection only,
# never loaded into os.environ.
_SECONDARY_ENV_RELPATHS = [
    "argumentation_analysis/.env",
    "config/.env",
]

# Variables whose divergence across .env files causes a silent 401.
_SENSITIVE_VARS = ["OPENAI_API_KEY", "OPENROUTER_API_KEY"]


def _mask(val: str) -> str:
    """Mask a secret for log output: first 8 chars + last 4 chars."""
    if len(val) <= 8:
        return "***"
    return f"{val[:8]}...{val[-4:]}"


def _env_key(name: str) -> str:
    """os.environ keys are case-insensitive, and stored upper-case, on Windows."""
    return name.upper() if os.name == "nt" else name


def set_by_caller(name: str) -> bool:
    """True while ``name`` still holds the value the process was started with.

    ``""`` counts: ``OPENAI_API_KEY= pytest ...`` asks for a keyless run. A value
    changed in-process since then (a sub-``.env`` loaded first by a module-level
    ``load_dotenv()``, #1295) is not the caller's.
    """
    key = _env_key(name)
    return (
        key in _CALLER_ENVIRONMENT and os.environ.get(name) == _CALLER_ENVIRONMENT[key]
    )


def load_env_file(path: Union[str, Path]) -> bool:
    """Load ``path`` into os.environ, except the variables the caller set.

    Its values replace any value set in-process before (another ``.env``), never
    a value the process was started with (#2472). Returns True when the file
    declares at least one variable, as ``load_dotenv`` does.
    """
    values = dotenv_values(dotenv_path=str(path))
    for name, value in values.items():
        if value is not None and not set_by_caller(name):
            os.environ[name] = value
    return bool(values)


def _find_repo_root() -> Optional[Path]:
    """Walk up from this file to find the repo root via pyproject.toml sentinel."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return None


class EnvironmentManager:
    """
    Handles loading and retrieving environment variables.

    Loading order (deterministic):
    1. Root .env (located via pyproject.toml sentinel). It replaces a value set
       in-process before it, e.g. by a sub-.env imported first (#1295), but not a
       value the caller started the process with, even "" (#2472). A caller-set
       key that differs from the root .env's is reported with a WARNING.
    2. Secondary .env files (argumentation_analysis/.env, config/.env) are NOT loaded;
       they are only parsed to detect divergence and emit a WARNING.
    3. Fallback: find_dotenv() legacy behaviour when no root .env is found; it
       only fills the variables that are not set.
    """

    def __init__(self) -> None:
        self.dotenv_path: str = ""
        self.dotenv_loaded: bool = False

        repo_root = _find_repo_root()
        root_env: Optional[Path] = (repo_root / ".env") if repo_root is not None else None

        if root_env is not None and root_env.exists():
            self.dotenv_path = str(root_env)
            self._check_caller_divergence(root_env)
            self.dotenv_loaded = load_env_file(root_env)
            if repo_root is not None:
                self._check_secondary_divergence(repo_root)
        else:
            # No root .env found — fall back to legacy find_dotenv behaviour.
            from dotenv import find_dotenv  # local import to avoid unconditional dep

            self.dotenv_path = find_dotenv()
            self.dotenv_loaded = load_dotenv(
                dotenv_path=self.dotenv_path or None, override=False
            )

    def _check_caller_divergence(self, root_env: Path) -> None:
        """Warn when a key the caller set shadows a different root .env key.

        The caller's value wins (#2472). An empty one asks for a keyless run and is
        not reported; a stale key exported in the shell would be, since it now
        beats the root .env as a sub-.env used to (#1295).
        """
        root_vals = dotenv_values(dotenv_path=str(root_env))
        for var in _SENSITIVE_VARS:
            caller_val = os.environ.get(var, "")
            root_val = root_vals.get(var) or ""
            if (
                set_by_caller(var)
                and caller_val
                and root_val
                and caller_val != root_val
            ):
                logger.warning(
                    "[EnvironmentManager] %s set by the caller (%s) differs from"
                    " the root .env (%s) — the caller's value is kept.",
                    var,
                    _mask(caller_val),
                    _mask(root_val),
                )

    def _check_secondary_divergence(self, repo_root: Path) -> None:
        """Parse secondary .env files and warn on OPENAI_API_KEY divergence."""
        canonical: dict[str, str] = {
            var: os.getenv(var, "") for var in _SENSITIVE_VARS
        }
        for rel in _SECONDARY_ENV_RELPATHS:
            secondary = repo_root / rel
            if not secondary.exists():
                continue
            secondary_vals: dict[str, str] = {}
            try:
                with open(secondary, encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        stripped = line.strip()
                        if not stripped or stripped.startswith("#") or "=" not in stripped:
                            continue
                        k, _, v = stripped.partition("=")
                        k = k.strip()
                        if k in _SENSITIVE_VARS:
                            secondary_vals[k] = v.strip().strip('"').strip("'")
            except OSError:
                continue
            for var, sec_val in secondary_vals.items():
                canon_val = canonical.get(var, "")
                if sec_val and canon_val and sec_val != canon_val:
                    logger.warning(
                        "[EnvironmentManager] %s divergence: value in effect=%s but"
                        " %s=%s — the value in effect is kept. Update or remove the"
                        " stale key.",
                        var,
                        _mask(canon_val),
                        rel,
                        _mask(sec_val),
                    )

    def get_variable(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves an environment variable."""
        return os.getenv(name, default)
