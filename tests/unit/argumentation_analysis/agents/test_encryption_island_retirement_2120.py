"""Né-rouge guards for #2120 — retirement of the unexecutable encryption island.

Arbitration R975 (issue #2120 comment): the encryption capability lives on the
living surface — ``core/io_manager.py`` (in-memory load/save of the encrypted
dataset, 6 production importers), ``services/crypto_service.py``,
``utils/crypto_workflow.py``, ``utils/update_encrypted_config.py`` and
``scripts/security/verify_encrypted_dataset_completeness.py``. The retired
``agents/tools/encryption/`` was a SECOND implementation that could not
execute at all: its orchestrator imported a module absent from the whole repo
(``create_and_archive_encrypted_config.py:31``), its key chain read
``ui.config.ENCRYPTION_KEY`` which is ``None`` even with ``.env`` loaded, and
its four guards pointed operators at ``TEXT_CONFIG_PASSPHRASE`` — a variable
the code never read. Zero importers, zero tests.

Function-by-function preservation proof (arbitration DoD) lives in the PR
body: every function has an equal-or-richer living equivalent, so nothing is
ported. ``deploy_and_run_scripts.ps1`` is retired with the island — its sole
purpose was deploying these four scripts (two of which no longer existed).
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
ISLAND = REPO_ROOT / "argumentation_analysis" / "agents" / "tools" / "encryption"
DEPLOY_COMPANION = (
    REPO_ROOT / "argumentation_analysis" / "agents" / "deploy_and_run_scripts.ps1"
)

# Point-in-time snapshots legitimately mention historical paths; living docs
# must not point at a retired island.
SNAPSHOT_DIRS = ("docs/reports/", "docs/archives/")
ISLAND_MARKERS = (
    "tools/encryption",
    "tools.encryption",
    "create_complete_encrypted_config",
    "create_and_archive_encrypted_config",
    "inspect_encrypted_file",
    "verify_encrypted_config",
    "deploy_and_run_scripts",
)
SCANNED_SUFFIXES = {".py", ".md", ".ps1", ".yml", ".yaml", ".json", ".txt"}


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def test_island_and_its_deploy_companion_are_retired_2120():
    assert not ISLAND.exists(), (
        f"{ISLAND} still exists — the R975 arbitration retired this "
        "unexecutable second implementation of the encryption capability"
    )
    assert not DEPLOY_COMPANION.exists(), (
        "deploy_and_run_scripts.ps1 only deployed the four island scripts "
        "(two of which no longer existed) — it must not outlive them"
    )


def test_no_dangling_island_references_in_living_docs_2120():
    """The misleading TEXT_CONFIG_PASSPHRASE guidance and the import examples
    died with the module — none of it may survive in a doc that stays."""
    offenders = []
    for rel in _tracked_files():
        if rel.startswith(SNAPSHOT_DIRS):
            continue
        if Path(rel).suffix.lower() not in SCANNED_SUFFIXES:
            continue
        if rel.startswith("tests/unit/argumentation_analysis/agents/"):
            continue  # this guard quotes the retired names deliberately
        try:
            text = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for marker in ISLAND_MARKERS:
            if marker in text:
                offenders.append(f"{rel}: {marker}")
                break
    assert (
        not offenders
    ), "Living files still reference the retired encryption island: " + "; ".join(
        offenders
    )


def test_living_surface_still_covers_the_capability_2120():
    """Control — the retirement must not orphan the dataset encryption path."""
    from argumentation_analysis.core.io_manager import (
        load_extract_definitions,
        save_extract_definitions,
    )
    from argumentation_analysis.services.crypto_service import CryptoService

    assert callable(load_extract_definitions)
    assert callable(save_extract_definitions)
    for method in (
        "derive_key_from_passphrase",
        "encrypt_data",
        "decrypt_data",
        "decrypt_and_decompress_json",
    ):
        assert callable(getattr(CryptoService, method)), (
            f"CryptoService.{method} must stay — the retired island's "
            "encrypt/decrypt/inspect functions were duplicates of it"
        )
    verify_script = (
        REPO_ROOT / "scripts" / "security" / "verify_encrypted_dataset_completeness.py"
    )
    assert verify_script.is_file(), (
        "verify_encrypted_dataset_completeness.py is the living "
        "verify-before-delete instrument (CLAUDE.md) — it must stay"
    )
    update_tool = (
        REPO_ROOT / "argumentation_analysis" / "utils" / "update_encrypted_config.py"
    )
    assert update_tool.is_file(), (
        "utils/update_encrypted_config.py is the living update path for the "
        "encrypted dataset — it must stay"
    )


if __name__ == "__main__":
    sys.exit(0)
