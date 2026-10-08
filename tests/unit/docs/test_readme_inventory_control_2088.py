"""#2088 — the README inventory's detection control must not need a defect.

``scripts/docs/inventory_argumentation_readmes.py`` (DoD item 1, the dated and
reproducible inventory) proved it could detect an undocumented directory by
asking the real tree for at least 5 of them. Once the Epic documented every
substantial directory, that control failed and the instrument exited 1 with
"inventaire non fiable" on a complete tree (measured on ``ecfd3a092``).

The control now plants synthetic directories through the same rule
``main()`` applies. These tests hold that the control passes, and that it
fails when the rule it guards is broken (mutation, not grep).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "docs"
    / "inventory_argumentation_readmes.py"
)


@pytest.fixture()
def inventory():
    spec = importlib.util.spec_from_file_location("_inventory_2088", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_detection_control_passes_without_a_defective_tree(inventory):
    ok, message = inventory._detection_control()
    assert ok, message


def test_control_fails_when_nothing_counts_as_substantial(inventory, monkeypatch):
    monkeypatch.setattr(inventory, "_is_substantial", lambda d, files: False)
    ok, message = inventory._detection_control()
    assert not ok
    assert "un .py sans README" in message


def test_control_fails_when_the_readme_is_ignored(inventory, monkeypatch):
    monkeypatch.setattr(inventory, "_needs_readme", inventory._is_substantial)
    ok, message = inventory._detection_control()
    assert not ok
    assert "un .py avec README" in message


def test_control_fails_when_vendored_roots_count(inventory, monkeypatch):
    monkeypatch.setattr(inventory, "VENDORED_ROOTS", ())
    ok, message = inventory._detection_control()
    assert not ok
    assert "racine vendorisée" in message
