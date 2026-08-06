"""Privacy audit for recorded LLM cassettes (#1603).

A cassette contains the LLM response, optionally with metadata. Per project
policy, no plaintext dataset content may appear in committed fixtures:

- raw_text / full_text / full_text_segment / raw_text_snippet (forbidden keys)
- Source names (heuristic — year ranges + author hints; PROVEN absent in the
  recorded subset used for the probe)
- Encrypted ciphertext is allowed (cannot be decrypted without the passphrase;
  useless alone)

The audit is a *blocking* gate at export time: a cassette with any forbidden
field listed raises and refuses to write.

Why blocking rather than warning: a silent privacy leak onto a tracked
surface (GitHub search index) is a release-blocker, not a lint warning.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

# Forbidden plaintext keys — checked recursively in any dict / list element.
# Names mirror `argumentation_analysis.core.io_manager` extraction schema.
FORBIDDEN_KEYS = frozenset((
    "raw_text",
    "full_text",
    "full_text_segment",
    "raw_text_snippet",
    "passphrase",  # never commit derived secrets
))

# Heuristic: politically sensitive corpus sources the dataset can contain.
# If any name appears in a cassette, the audit fails.
# Source: project CLAUDE.md "Dataset Privacy Discipline" + the canonical
# dataset is political speeches (historical dictators, current heads of state).
# This list is intentionally narrow — broader NER catches false positives.
# Last update: 2026-08-06 (#1603 R758).
SOURCE_NAME_HINTS = (
    "Trump", "Biden", "Macron", "Le Pen", "Mélenchon", "Melenchon",
    "Poutine", "Zelensky", "Zelenskyy", "Mussolini", "Hitler",
    "Pétain", "Petain", "Staline", "Stalin",
    "Bachelet", "Milei", "Bolsonaro", "Orbán", "Orban",
)

# Historical political date range — corpus contains (year: 1933-2026).
DATE_RE = re.compile(r"\b(19[3-9]\d|20[0-2]\d)\b")


def audit_value(value: Any, *, source: str = "<unknown>") -> list[str]:
    """Return a list of privacy violation descriptions (empty == safe).

    Walks ``value`` recursively and checks for any forbidden key, source
    name, or historical political date. Strict-mode is intentional: a
    cassette that fails this audit cannot be committed.
    """
    violations: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k in FORBIDDEN_KEYS:
                    violations.append(
                        f"{source}: forbidden key {k!r} at {path}.{k}"
                    )
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")
        elif isinstance(node, str):
            # Source name / date hints — only on text-sized strings, not on
            # the role field etc. (which is short anyway).
            if len(node) < 20:
                return
            for name in SOURCE_NAME_HINTS:
                if name in node:
                    violations.append(
                        f"{source}: source-name hint {name!r} found at {path}"
                    )
                    break  # one report per node is enough
            for year in DATE_RE.findall(node):
                # 1933..2026 are the politically sensitive corpus years.
                # Earlier (1920s debates etc.) would slip by design — broader
                # range adds false positives on test fixtures.
                violations.append(
                    f"{source}: historical-year hint {year} found at {path}"
                )

    walk(value, "")
    return violations


def assert_safe(value: Any, *, source: str) -> None:
    """Raise ``PrivacyViolation`` if ``value`` fails the audit."""
    v = audit_value(value, source=source)
    if v:
        raise PrivacyViolation(v)


class PrivacyViolation(RuntimeError):
    """Raised when an LLM cassette response contains forbidden content."""

    def __init__(self, violations: list[str]) -> None:
        super().__init__(
            "Cassette refused — privacy violations:\n  - " + "\n  - ".join(violations)
        )
        self.violations = violations
