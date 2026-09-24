# -*- coding: utf-8 -*-
"""#2402 (what remained): a lone surrogate in a failure message killed the
xdist worker, and the session lost its OTHER tracebacks.

Measured pre-fix: the probe below ends in INTERNALERROR (``RuntimeError:
Unexpectedly no active workers available``) with no failures section — the
ordinary failure next to it was reported as a bare count. The repair wraps
``pytest_report_to_serializable`` in ``tests/conftest.py`` with
``tests/_xdist_report_serialization.sanitize_report_data``: the non-encodable
strings are escaped and the cause is named.
"""

from tests._xdist_report_serialization import NOTE, sanitize_report_data
from tests.nested_pytest import both, run_probe

_SURROGATE_PROBE = """
def test_a_lone_surrogate_in_the_message():
    raise AssertionError("boom \\ud800 tail")


def test_b_forced_failure():
    assert False, "forced failure 2402"
"""


class TestSanitizeReportData:
    def test_plain_data_is_untouched(self):
        data = {"longrepr": ("f.py", 3, "plain"), "sections": [("cap", "ok")]}
        same, escaped = sanitize_report_data(data)
        assert same == data
        assert escaped == 0

    def test_a_surrogate_string_is_escaped_and_named(self):
        data, escaped = sanitize_report_data(("f.py", 3, "boom \ud800 tail"))
        assert escaped == 1
        assert data[2].startswith("boom \\ud800 tail")
        assert NOTE in data[2]
        data[2].encode("utf-8")  # what execnet refused before the repair

    def test_a_surrogate_in_a_nested_container_is_found(self):
        data, escaped = sanitize_report_data(
            {"sections": [("t", "x \udfff"), {"k": ["y \ud83d"]}]}
        )
        assert escaped == 2
        assert isinstance(data["sections"], list)
        assert isinstance(data["sections"][1], dict)
        assert isinstance(data["sections"][1]["k"], list)
        for text in (data["sections"][0][1], data["sections"][1]["k"][0]):
            assert NOTE in text
            text.encode("utf-8")

    def test_a_clean_report_keeps_its_container_types(self):
        data = {"sections": [("t", "ok")], "longrepr": ("f.py", 1, "x")}
        same, escaped = sanitize_report_data(data)
        assert escaped == 0
        assert isinstance(same["sections"], list)
        assert isinstance(same["sections"][0], tuple)
        assert isinstance(same["longrepr"], tuple)


class TestTheSessionKeepsItsOtherTracebacks:
    def test_under_xdist_a_surrogate_failure_no_longer_kills_the_worker(self):
        returncode, out, err = run_probe(
            "2402x",
            {"probe_2402_serialization.py": _SURROGATE_PROBE},
            "-n",
            "1",
            "--disable-jvm-session",
        )
        text = out + err
        assert "INTERNALERROR" not in text, both(out, err)
        assert "boom" in text, both(out, err)
        assert "forced failure 2402" in text, both(out, err)
        assert "lone surrogate" in text, both(out, err)  # the cause is named
        assert returncode == 1, both(out, err)
