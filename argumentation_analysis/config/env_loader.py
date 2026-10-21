# -*- coding: utf-8 -*-
"""
Manages environment variables for the project.
Loads root .env deterministically: it wins over sub-.env files (#1295) and loses
to the values the caller started the process with, even "" (#2472) — in this
process and in every child it spawns (#3019).
Warns when secondary .env files carry a different OPENAI_API_KEY.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Optional, Union

from dotenv import dotenv_values

logger = logging.getLogger(__name__)

# The non-empty carrier of the caller's neutralisations (#3019). On Windows,
# restoring os.environ (clear() + update(saved), or patch.dict(clear=True))
# erases every ""-valued name from the process block: Python's dict keeps "",
# but a child spawned with the default env=None inherits no name at all, and its
# loader fills the key from the root .env — routing a replay test to another
# provider (the cache key drifts, the cassette misses) and, outside replay,
# spending through .env from a neutralised run (the R1073 class). The carrier is
# non-empty on purpose: a restore never erases it, so the names survive the
# boundary and every import of this module re-asserts them as "" before the
# snapshot below reads the environment.
_CALLER_EMPTY_NAMES_VAR = "CALLER_EMPTY_NAMES"


def _carry_caller_empty_names() -> None:
    """Export the caller-empty names for children, or re-assert the carried ones.

    Root process (no carrier): the variables the caller left empty are the
    caller's neutralisations — a value the caller set wins over the root .env
    even "" (#2472) — so their names are exported in a non-empty carrier a
    restore cannot erase. Child process (carrier present): a carried name the
    boundary erased is re-asserted as "", before ``_CALLER_ENVIRONMENT``
    captures the environment; a carried name that holds a value is left alone —
    an explicit ``env=`` outranks the carrier.
    """
    carried = os.environ.get(_CALLER_EMPTY_NAMES_VAR)
    if carried:
        for name in carried.split(","):
            if name and name != _CALLER_EMPTY_NAMES_VAR and name not in os.environ:
                try:
                    os.environ[name] = ""
                except ValueError:  # a tampered carrier must not break the import
                    continue
        return
    empty = sorted(
        name
        for name, value in os.environ.items()
        if value == "" and name != _CALLER_EMPTY_NAMES_VAR
    )
    if empty:
        os.environ[_CALLER_EMPTY_NAMES_VAR] = ",".join(empty)


_carry_caller_empty_names()

# The environment the caller started the process with, captured when this module
# is first imported: before EnvironmentManager has loaded any .env (#2472), and
# after the caller's neutralisations were re-asserted (#3019).
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


def load_env_file(path: Union[str, Path], fill_only: bool = False) -> bool:
    """Load ``path`` into os.environ, except the variables the caller set.

    Its values replace any value set in-process before (another ``.env``), never
    a value the process was started with (#2472). Returns True when the file
    declares at least one variable, as ``load_dotenv`` does.

    ``fill_only=True`` is the import-time contract (#3116): a name the process
    already carries is left alone, whatever set it and whenever — so an
    auto-load triggered by an unrelated import can never stomp a value a caller
    imposed after ``_CALLER_ENVIRONMENT`` was captured. Names the process lacks
    are still filled, which is what importing ``core.environment`` for
    "auto-activation" promises its consumers (#2130). Explicit constructions
    keep the replacing policy (#1295).
    """
    values = dotenv_values(dotenv_path=str(path))
    for name, value in values.items():
        if value is None:
            continue
        if fill_only:
            if name not in os.environ:
                os.environ[name] = value
            continue
        if not set_by_caller(name):
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
       value the caller started the process with, even "" (#2472) — in this
       process and in every child it spawns (#3019). A caller-set
       key that differs from the root .env's is reported with a WARNING.
    2. Secondary .env files (argumentation_analysis/.env, config/.env) are NOT loaded;
       they are only parsed to detect divergence and emit a WARNING.
    3. No root .env: nothing is loaded (#2707). The old find_dotenv() fallback
       walked up from this module, past the checkout, and loaded the first .env
       it met, above the checkout too (a worktree under D: loaded another
       project's .env). A checkout without its .env is a keyless run.

    ``fill_only=True`` is for the import-time auto-loads (#3116): they fill the
    names the process lacks and never replace one it carries. An explicit
    construction keeps the full policy above.
    """

    def __init__(self, *, fill_only: bool = False) -> None:
        self.dotenv_path: str = ""
        self.dotenv_loaded: bool = False

        repo_root = _find_repo_root()
        root_env: Optional[Path] = (
            (repo_root / ".env") if repo_root is not None else None
        )

        if root_env is not None and root_env.exists():
            self.dotenv_path = str(root_env)
            self._check_caller_divergence(root_env)
            self.dotenv_loaded = load_env_file(root_env, fill_only=fill_only)
            if repo_root is not None:
                self._check_secondary_divergence(repo_root)

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
        canonical: dict[str, str] = {var: os.getenv(var, "") for var in _SENSITIVE_VARS}
        for rel in _SECONDARY_ENV_RELPATHS:
            secondary = repo_root / rel
            if not secondary.exists():
                continue
            secondary_vals: dict[str, str] = {}
            try:
                with open(secondary, encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        stripped = line.strip()
                        if (
                            not stripped
                            or stripped.startswith("#")
                            or "=" not in stripped
                        ):
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
