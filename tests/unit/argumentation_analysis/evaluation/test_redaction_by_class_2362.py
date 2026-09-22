"""#2362 B1 — redaction behavior pinned across the hand-list → class-vocabulary move.

The production sweep (#2349) measures the PRESENCE of class names in tracked
files; it is blind to what the redactors ELIMINATE. Deriving the person
alternation from ``PERSON_PATTERNS`` changes coverage — here it widens it —
and a presence sweep cannot witness that change. These tests are the behavior
half of the instrument: a class person redacted from an export value, the
snake_case form caught in a KEY, the public figures outside the class lists
still redacted (a scrubber may grow, never shrink silently — #1019), and the
log anonymizer doing the same on both halves.

Privacy HARD: every class-member input is DERIVED at runtime from
``PERSON_PATTERNS`` — no member spelling lives in this file (the tests/ sweep
#2004 would flag it), the same discipline as the #2349 guard's own control.
"""

from __future__ import annotations

from pathlib import Path

from argumentation_analysis.evaluation.leak_patterns import PERSON_PATTERNS
from argumentation_analysis.evaluation.state_export_scrub import (
    _NEVER_MATCHES,
    _global_entity_scrub,
)


def _one_ascii_person() -> str:
    persons = [p for p in PERSON_PATTERNS if p.isascii() and p.isalpha()]
    assert (
        persons
    ), "PERSON_PATTERNS carries no plain ascii member to derive a test input"
    return persons[0]


class TestExportEntityScrub:
    def test_class_person_in_value_is_scrubbed(self):
        name = _one_ascii_person()
        assert (
            _global_entity_scrub(f"statement by {name}", instance_re=_NEVER_MATCHES)
            == "<scrubbed>"
        )

    def test_class_person_inside_snake_key_is_scrubbed(self):
        name = _one_ascii_person()
        out = _global_entity_scrub(
            {f"{name.lower()}_flag": "ok"}, instance_re=_NEVER_MATCHES
        )
        # the offending KEY is replaced (renamed key_0); the clean value survives
        assert list(out) == ["key_0"]
        assert out["key_0"] == "ok"

    def test_extra_public_person_outside_class_lists_still_scrubbed(self):
        # Not PERSON_PATTERNS members: deriving from the class list must not
        # narrow the scrubber — the extras stay until the class vocabulary
        # itself is arbitrated (Q-R1042-A family).
        assert (
            _global_entity_scrub("about obama", instance_re=_NEVER_MATCHES)
            == "<scrubbed>"
        )
        assert (
            _global_entity_scrub("the pentagon said", instance_re=_NEVER_MATCHES)
            == "<scrubbed>"
        )


class TestLogAnonymizer:
    def test_log_anonymizer_scrubs_class_person_and_extras(self, tmp_path: Path):
        from scripts.utils.cleanup_sensitive_traces import (
            SensitiveDataCleaner,
            _build_sensitive_patterns,
        )

        name = _one_ascii_person()
        log = tmp_path / "run.log"
        log.write_text(
            f"{name} spoke; Mao agreed; see https://example.com/political/notes\n",
            encoding="utf-8",
        )
        cleaner = SensitiveDataCleaner(dry_run=False)
        cleaner._anonymize_file(log, _build_sensitive_patterns())
        scrubbed = log.read_text(encoding="utf-8")
        # the derived class member AND the extra outside the class lists
        assert scrubbed.count("[LEADER]") >= 2
        assert "[POLITICAL_URL]" in scrubbed
