# -*- coding: utf-8 -*-
"""
Manages environment variables for the project.
Loads root .env deterministically (override=True so root wins over sub-.env files).
Warns when secondary .env files carry a different OPENAI_API_KEY.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

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
    1. Root .env (located via pyproject.toml sentinel) — loaded with override=True so it
       always wins, even if a sub-.env was previously imported.
    2. Secondary .env files (argumentation_analysis/.env, config/.env) are NOT loaded;
       they are only parsed to detect divergence and emit a WARNING.
    3. Fallback: find_dotenv() legacy behaviour when no root .env is found.
    """

    def __init__(self, override: bool = False) -> None:
        self.dotenv_path: str = ""
        self.dotenv_loaded: bool = False

        repo_root = _find_repo_root()
        root_env: Optional[Path] = (repo_root / ".env") if repo_root is not None else None

        if root_env is not None and root_env.exists():
            self.dotenv_path = str(root_env)
            # override=True: root .env is canonical; beats any value already in os.environ
            # (e.g. from a sub-.env loaded earlier via first-import-wins).
            self.dotenv_loaded = load_dotenv(dotenv_path=str(root_env), override=True)
            if repo_root is not None:
                self._check_secondary_divergence(repo_root)
        else:
            # No root .env found — fall back to legacy find_dotenv behaviour.
            from dotenv import find_dotenv  # local import to avoid unconditional dep

            self.dotenv_path = find_dotenv()
            self.dotenv_loaded = load_dotenv(
                dotenv_path=self.dotenv_path or None, override=override
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
                        "[EnvironmentManager] %s divergence: root .env=%s but %s=%s"
                        " — root value retained. Update or remove the stale key.",
                        var,
                        _mask(canon_val),
                        rel,
                        _mask(sec_val),
                    )

    def get_variable(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves an environment variable."""
        return os.getenv(name, default)
