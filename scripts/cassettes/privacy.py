"""Privacy audit for recorded LLM cassettes (#1603).

A cassette contains the LLM response, optionally with metadata. Per project
policy, no plaintext dataset content may appear in committed fixtures:

- raw_text / full_text / full_text_segment / raw_text_snippet (forbidden keys)
- Source names — the shared class-vocabulary detector ``PERSON_RE`` from
  ``argumentation_analysis/evaluation/leak_patterns.py`` (#2362 class A,
  option 4: one vocabulary for every instrument; the hand-copied list that
  lived here could drift from the class vocabulary in silence)
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

from argumentation_analysis.evaluation.leak_patterns import PERSON_RE

# Forbidden plaintext keys — checked recursively in any dict / list element.
# Names mirror `argumentation_analysis.core.io_manager` extraction schema.
FORBIDDEN_KEYS = frozenset(
    (
        "raw_text",
        "full_text",
        "full_text_segment",
        "raw_text_snippet",
        "passphrase",  # never commit derived secrets
    )
)

# Historical political date range — corpus contains (year: 1933-2026).
DATE_RE = re.compile(r"\b(19[3-9]\d|20[0-2]\d)\b")

# A year match glued to a currency symbol is a monetary amount, not a date
# ("€2000 to run a tournament", "budget de 2000 €"). Measured on the #1603
# harvest: governance/debate scenario responses carry budget figures that the
# bare date regex refused. #2300 extends the markers beyond symbols to
# unambiguous currency words: the symbols-only line refused every cassette of
# the two deliberation tests on « 2000 euros » — the natural French spelling
# of an amount — blocking the replay band on a measured false-positive class.
# Words are limited to denomination words that are never prose-ambiguous
# ("livres" also means books — excluded).
CURRENCY_SYMBOLS = "€$£¥"
CURRENCY_WORD_RE = re.compile(
    r"^(?:euros?|eur|dollars?|usd|gbp|yens?)\b", re.IGNORECASE
)
_AMOUNT_SPACES = "   "


def _is_monetary_amount(text: str, match: re.Match) -> bool:
    before = text[: match.start()].rstrip(_AMOUNT_SPACES)
    after = text[match.end() :].lstrip(_AMOUNT_SPACES)
    if before and before[-1] in CURRENCY_SYMBOLS:
        return True
    if after and after[0] in CURRENCY_SYMBOLS:
        return True
    return bool(after and CURRENCY_WORD_RE.match(after))


# Response-metadata fields where the year/name heuristics are meaningless:
# the OpenAI `model` id is versioned ("gpt-5-mini-2025-08-07") and would trip
# the date rule on every raw-path cassette; `id`/`created`/`system_fingerprint`
# are opaque service stamps. Forbidden-key checks still apply to dict KEYS
# everywhere; only the string heuristics are skipped on these fields. #1603.
METADATA_KEYS = frozenset(
    (
        "model",
        "id",
        "created",
        "object",
        "service_tier",
        "system_fingerprint",
        "finish_reason",
        "index",
        "role",
    )
)


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
                    violations.append(f"{source}: forbidden key {k!r} at {path}.{k}")
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")
        elif isinstance(node, str):
            # Source name / date hints — only on text-sized strings, not on
            # the role field etc. (which is short anyway).
            if len(node) < 20:
                return
            # Skip response-metadata keys (versioned model ids, opaque stamps)
            # — never corpus prose.
            last = path.split(".")[-1]
            m = re.match(r"(.+)\[\d+\]$", last)
            if m:
                last = m.group(1)
            if last in METADATA_KEYS:
                return
            name_hit = PERSON_RE.search(node)
            if name_hit:
                violations.append(
                    f"{source}: source-name hint {name_hit.group(0)!r} found at {path}"
                )
            for m in DATE_RE.finditer(node):
                if _is_monetary_amount(node, m):
                    continue
                # 1933..2026 are the politically sensitive corpus years.
                # Earlier (1920s debates etc.) would slip by design — broader
                # range adds false positives on test fixtures.
                violations.append(
                    f"{source}: historical-year hint {m.group(1)} found at {path}"
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
