"""Witness for #3551: the scanned posting helper, tracked.

Every command refuses before any ``gh`` call, the writing account's token
rides one command's environment (never a global switch, never displayed),
and the bare 8-hex refusal is per token: a commit sha on the same line
does not excuse a document id beside it. No network, no key, no corpus —
the tests replace the ``gh`` seam.

The fake document id is built at run time from two halves, so no 8-hex
literal enters this file.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.coordination import post_tracker

FAKE_ID = "a1b2" + "c3d4"  # 8 hex, letters and digits — built at run time
NINE_CHAR_SHA = "1a2b3c4d5"  # 9 hex: the shape a quoted commit sha takes


class RecordingGh:
    """A stand-in for ``post_tracker._gh`` that records calls."""

    def __init__(self):
        self.calls: list[tuple[tuple, dict]] = []

    def __call__(self, args, **kwargs):
        self.calls.append((tuple(args), dict(kwargs)))
        return subprocess.CompletedProcess(
            args=["gh", *args],
            returncode=0,
            stdout="https://example/issue/4242\n",
            stderr="",
        )


@pytest.fixture
def recorder(monkeypatch):
    rec = RecordingGh()
    monkeypatch.setattr(post_tracker, "_gh", rec)
    return rec


class TestTheSecondNet:
    def test_a_bare_eight_hex_token_with_letter_and_digit_is_refused(self):
        refusals = post_tracker.scan_string(f"see doc {FAKE_ID} for the rest")
        assert any("8-hex" in r for r in refusals)

    def test_a_nine_character_sha_quoted_alone_is_clean(self):
        assert post_tracker.scan_string(f"rebased on {NINE_CHAR_SHA}") == []

    def test_a_sha_on_the_same_line_does_not_excuse_a_bare_id_beside_it(self):
        """The dispatch's synthetic case (#3551): per TOKEN, not per line."""
        text = f"fix on top of {NINE_CHAR_SHA} touches {FAKE_ID} only"
        assert any("8-hex" in r for r in post_tracker.scan_string(text))

    def test_an_all_digit_run_like_a_date_is_not_an_identifier(self):
        assert post_tracker.scan_string("recorded on 20261118 by hand") == []

    def test_an_all_letter_hex_run_is_not_the_mixed_shape(self):
        assert post_tracker.scan_string("the mask deadbeef is the mask") == []


class TestTheScannerNet:
    def test_a_scanner_hit_is_surfaced_as_a_refusal(self, monkeypatch):
        monkeypatch.setattr(post_tracker, "scan_text", lambda text: 2)
        refusals = post_tracker.scan_string("anything")
        assert any("repository scanner" in r for r in refusals)

    def test_a_clean_text_has_no_refusals(self, monkeypatch):
        monkeypatch.setattr(post_tracker, "scan_text", lambda text: 0)
        assert post_tracker.scan_string("clean prose, no token") == []


class TestNoGhCallWhenTheScanFails:
    @pytest.fixture
    def bad_text(self, tmp_path: Path) -> Path:
        f = tmp_path / "draft.md"
        f.write_text(
            f"TITLE: mentions {FAKE_ID}\n\nbody quotes {FAKE_ID}", encoding="utf-8"
        )
        return f

    def test_new_refuses_before_gh(self, recorder, bad_text, tmp_path):
        rc = post_tracker.cmd_new(
            bad_text, labels="", repo="o/r", user=None, numbers=tmp_path / "numbers.tsv"
        )
        assert rc == 3
        assert recorder.calls == []

    def test_comment_refuses_before_gh(self, recorder, bad_text):
        assert post_tracker.cmd_comment(12, bad_text, repo="o/r", user=None) == 3
        assert recorder.calls == []

    def test_title_refuses_before_gh(self, recorder):
        assert (
            post_tracker.cmd_title(12, f"new title {FAKE_ID}", repo="o/r", user=None)
            == 3
        )
        assert recorder.calls == []

    def test_body_refuses_before_gh(self, recorder, bad_text):
        assert post_tracker.cmd_body(12, bad_text, repo="o/r", user=None) == 3
        assert recorder.calls == []

    def test_close_refuses_before_gh(self, recorder, bad_text):
        assert (
            post_tracker.cmd_close(
                12, bad_text, reason="completed", repo="o/r", user=None
            )
            == 3
        )
        assert recorder.calls == []


class TestTheHappyPathUsesTheSeam:
    @pytest.fixture
    def good_draft(self, tmp_path: Path) -> Path:
        f = tmp_path / "draft.md"
        f.write_text("TITLE: a clean title\n\na clean body", encoding="utf-8")
        return f

    def test_new_calls_gh_once_and_records_the_number(
        self, recorder, good_draft, tmp_path
    ):
        numbers = tmp_path / "numbers.tsv"
        rc = post_tracker.cmd_new(
            good_draft, labels="queue", repo="o/r", user=None, numbers=numbers
        )
        assert rc == 0
        assert len(recorder.calls) == 1
        args = recorder.calls[0][0]
        assert args[0] == "issue"
        assert "create" in args
        assert numbers.read_text(encoding="utf-8").endswith("4242\n")

    def test_the_token_never_enters_the_command_nor_the_output(
        self, monkeypatch, good_draft, tmp_path, capsys
    ):
        """GH_TOKEN rides the environment, not argv, and is never printed."""
        seen_env: dict = {}

        def fake_gh(args, *, env=None, **kwargs):
            seen_env.update(env or {})
            return subprocess.CompletedProcess(
                args=list(args), returncode=0, stdout="ok", stderr=""
            )

        def fake_token(*a, **k):
            return subprocess.CompletedProcess(
                args=list(a), returncode=0, stdout="tok-value-not-a-token\n", stderr=""
            )

        monkeypatch.setattr(post_tracker, "_gh", fake_gh)
        monkeypatch.setattr(post_tracker, "_token_for", fake_token)
        rc = post_tracker.cmd_comment(7, good_draft, repo="o/r", user="some-account")
        assert rc == 0
        assert seen_env.get("GH_TOKEN") == "tok-value-not-a-token"
        assert "tok-value-not-a-token" not in capsys.readouterr().out


class TestTheCli:
    def test_scan_exits_nonzero_on_a_refused_file(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(post_tracker, "scan_text", lambda text: 1)
        f = tmp_path / "t.md"
        f.write_text("scanner refuses this", encoding="utf-8")
        rc = post_tracker.main(["scan", str(f)])
        assert rc == 1

    def test_scan_exits_zero_on_a_clean_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(post_tracker, "scan_text", lambda text: 0)
        f = tmp_path / "t.md"
        f.write_text(f"clean, quotes {NINE_CHAR_SHA}", encoding="utf-8")
        assert post_tracker.main(["scan", str(f)]) == 0
