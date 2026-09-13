"""Guard: every ``settings.X`` chain read by production resolves (#2115).

#2115 found a schema-drift family: consumers read attributes on the
``settings`` singleton that ``AppSettings`` does not carry. Two were live
defects, both silent:

- ``service_setup/analysis_services.py`` read ``settings.default_model_id``
  (the field lives at ``settings.service_manager.default_model_id``) — the
  ``AttributeError`` was swallowed by the surrounding ``except Exception``,
  so EVERY run (mock included) built ``llm_service = None``;
- ``kernel/kernel_builder.py`` read ``settings.azure_openai``, but the block
  lives at ``settings.jvm.azure_openai`` — the azure branch therefore raised
  ``AttributeError`` before its own "key not configured" check, and could
  never run.

The census below is deliberately NOT an allow-list: it walks every module in
``argumentation_analysis/`` that imports the ``settings`` singleton and
resolves every ``settings.a.b…`` chain by ``getattr`` against the live object.
Existence is what the defect class is about, so the check needs no annotation
walking and no pydantic knowledge — and a phantom introduced anywhere in the
production tree reddens, not only in the two modules of record.

Chains that hit a ``None`` mid-way are counted as *unverifiable* rather than
failed: a value that is legitimately absent at rest (an unset optional
secret) can hide a phantom further down, and the guard says so instead of
pretending it checked.
"""

import ast
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
PROD_ROOT = PROJECT_ROOT / "argumentation_analysis"

# The singleton import; a module-level ``settings`` NAME is what makes a bare
# ``settings.X`` chain refer to the production configuration object.
_SINGLETON_IMPORT = re.compile(
    r"^from\s+argumentation_analysis\.config\.settings\s+import\s+\(?[^)]*\bsettings\b",
    re.M,
)


def _module_source(py: Path) -> str:
    # utf-8-sig: at least one production module starts with a BOM, which
    # ast.parse rejects outright.
    return py.read_text(encoding="utf-8-sig")


def _singleton_modules() -> list[Path]:
    return [
        py
        for py in sorted(PROD_ROOT.rglob("*.py"))
        if _SINGLETON_IMPORT.search(_module_source(py))
    ]


def _attribute_chain(node: ast.Attribute) -> list[str] | None:
    """['settings', 'jvm', 'azure_openai'] for a settings-rooted chain."""
    parts: list[str] = []
    cur: ast.expr = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return list(reversed(parts))
    return None


def _settings_chains() -> dict[tuple[str, ...], set[str]]:
    """Chain -> set of production modules reading it."""
    chains: dict[tuple[str, ...], set[str]] = {}
    for py in _singleton_modules():
        tree = ast.parse(_module_source(py))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue
            chain = _attribute_chain(node)
            if chain and chain[0] == "settings" and len(chain) > 1:
                chains.setdefault(tuple(chain), set()).add(
                    py.relative_to(PROJECT_ROOT).as_posix()
                )
    return chains


def _resolve(chain: tuple[str, ...]) -> tuple[bool, bool]:
    """(resolved, verifiable) — walk the live singleton with getattr.

    ``verifiable`` is False when a legitimate ``None`` stops the walk before
    the last segment: the chain is not proven broken, only unproven.
    """
    from argumentation_analysis.config.settings import settings

    obj: object = settings
    for index, segment in enumerate(chain[1:], start=1):
        if not hasattr(obj, segment):
            return False, True
        obj = getattr(obj, segment)
        if obj is None and index < len(chain) - 1:
            return True, False
    return True, True


def test_census_is_alive():
    """Floor: the census reads a real surface, not an empty one.

    A guard that scans nothing passes for the wrong reason; the R987 lesson
    (a census filtered by a stale allow-list measures the list, not the
    surface) applies here too, so the floor pins a measured minimum.
    """
    modules = _singleton_modules()
    chains = _settings_chains()
    assert len(modules) >= 15, (
        f"only {len(modules)} module(s) importing the settings singleton — "
        f"the import regex or the tree layout drifted"
    )
    assert len(chains) >= 30, (
        f"only {len(chains)} settings.* chain(s) found — the AST census is "
        f"stale (renamed singleton? moved package?)"
    )


def test_no_phantom_settings_attribute():
    """Every ``settings.X…`` chain in production resolves at runtime."""
    broken: dict[str, str] = {}
    for chain, modules in sorted(_settings_chains().items()):
        resolved, _verifiable = _resolve(chain)
        if not resolved:
            broken[".".join(chain)] = ", ".join(sorted(modules))
    assert not broken, (
        f"settings attribute chains that raise AttributeError at runtime: "
        f"{broken}. AppSettings does not carry these names — either read the "
        f"one that exists (nested settings live under settings.jvm / "
        f"settings.service_manager / settings.openai / settings.ui…) or add "
        f"the field. A swallowed AttributeError is how #2115 made the LLM "
        f"service None on every run without a single visible failure."
    )


def test_unverifiable_chains_are_reported_not_silent():
    """The guard states what it could not check (no false comfort)."""
    unverifiable: dict[str, str] = {}
    for chain, modules in sorted(_settings_chains().items()):
        resolved, verifiable = _resolve(chain)
        if resolved and not verifiable:
            unverifiable[".".join(chain)] = ", ".join(sorted(modules))
    # Not an assertion on emptiness: an unset optional secret is legitimate.
    # The assertion is that the count stays small enough to remain reviewable.
    assert len(unverifiable) <= 5, (
        f"too many unverifiable chains ({len(unverifiable)}): {unverifiable} "
        f"— a None mid-chain now hides large parts of the surface"
    )


def test_the_guard_detects_a_phantom():
    """Positive control: the detector is not vacuous.

    ``settings.definitely_not_a_field`` must fail resolution — otherwise
    ``test_no_phantom_settings_attribute`` would pass on any input, which is
    the "instrument that renders the same value everywhere" failure mode.
    """
    resolved, _verifiable = _resolve(("settings", "definitely_not_a_field"))
    assert not resolved, "the resolver accepted a fabricated phantom attribute"


@pytest.mark.parametrize(
    "chain",
    [
        ("settings", "default_model_id"),  # #2115 cas 1 — top-level phantom
        ("settings", "azure_openai"),  # #2115 cas 2 — misnested field
    ],
)
def test_the_two_historical_phantoms_stay_detected(chain):
    """The two defects of record are exactly what the guard rejects."""
    resolved, _verifiable = _resolve(chain)
    assert not resolved, (
        f"{'.'.join(chain)} resolves again — either the field was (re)added "
        f"at the top level, in which case remove this pin, or a shim was "
        f"introduced to silence the guard"
    )
