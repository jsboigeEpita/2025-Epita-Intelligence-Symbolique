"""#3375 — the v1 panel selects the SAME documents on both arms.

The panel's DoD: ``run_corpus_batch.py`` and ``run_zeroshot_arm.py`` take the
same nine-plus-one document list, and a dry-run lists exactly those. Two
re-implementations would drift (that is #2841's rule 4, which the panel
inherits), so the selection is parsed once, in ``parse_doc_ids``, and applied
once, inside ``expand_corpus`` — the function both arms already call.

What the witnesses kill, one shape each:

- a selection that silently falls back to the whole corpus (an empty panel
  reporting every arm as trivially equal);
- an id typo that shortens the panel instead of failing (nine documents
  reported as ten);
- a panel re-sorted into corpus order, which would reorder the verdict table
  under the reader;
- an arm that takes the flag and does not pass it on.

No network, no dataset: the definitions are synthetic and every arm call is
either a dry-run or a spy on the seam.

The witnesses carry their OWN salt (an autouse fixture sets a synthetic
``OPAQUE_ID_SALT``): a seat's ``.env`` lending the real one made the module
green at home and red on the gate, which has no secret (#3383 CI run
41662307353 — 5 failed, one cause). The expected ids are derived from
``opaque_id(name, salt=…)`` rather than read back from ``expand_corpus``,
and one witness proves in a child process that production refuses — loudly —
when no salt exists anywhere (a public default would turn every opaque id
into a confirmation oracle, #1973).
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SALT = "synthetic-test-salt-3375"

sys.path.insert(0, str(REPO_ROOT))

from argumentation_analysis.evaluation.opaque_id import opaque_id
from scripts.dataset import run_corpus_batch as batch
from scripts.dataset import run_zeroshot_arm as arm


@pytest.fixture(autouse=True)
def _synthetic_salt(monkeypatch):
    """The witnesses never borrow the seat's real salt — that is the CI red."""
    monkeypatch.setenv("OPAQUE_ID_SALT", SALT)


def _definitions():
    """Three sources: two single-extract, one with two extracts."""
    return [
        {"source_name": "src_one", "extracts": [{"extract_text": "texte un."}]},
        {"source_name": "src_two", "extracts": [{"extract_text": "texte deux."}]},
        {
            "source_name": "src_three",
            "extracts": [
                {"extract_text": "texte trois a."},
                {"extract_text": "texte trois b."},
            ],
        },
    ]


def _ids():
    """Expected ids, derived independently of the code under test.

    Reading them back from ``expand_corpus`` would make every panel witness
    tautological: both sides of the assert would be the same call. The ids
    come from ``opaque_id(salt)`` plus the ``_extN`` suffix multi-extract
    sources carry.
    """
    one = opaque_id("src_one", salt=SALT)
    two = opaque_id("src_two", salt=SALT)
    three = opaque_id("src_three", salt=SALT)
    return [one, two, f"{three}_ext0", f"{three}_ext1"]


class TestParsing:
    def test_a_comma_list_keeps_its_order(self):
        assert batch.parse_doc_ids("b,a,c") == ["b", "a", "c"]

    def test_whitespace_separates_like_commas(self):
        assert batch.parse_doc_ids("b  a,\tc\n") == ["b", "a", "c"]

    def test_a_repeated_id_runs_once_first_wins(self):
        assert batch.parse_doc_ids("b,a,b") == ["b", "a"]

    def test_a_panel_file_ignores_comments_and_blanks(self, tmp_path):
        panel = tmp_path / "panel.txt"
        panel.write_text(
            "# the v1 panel\nb\n\n  a  # trailing note\n", encoding="utf-8"
        )
        assert batch.parse_doc_ids(None, str(panel)) == ["b", "a"]

    def test_flag_and_file_are_concatenated_and_deduplicated(self, tmp_path):
        panel = tmp_path / "panel.txt"
        panel.write_text("c\na\n", encoding="utf-8")
        assert batch.parse_doc_ids("a,b", str(panel)) == ["a", "b", "c"]

    def test_no_selection_is_none(self):
        assert batch.parse_doc_ids() is None

    def test_an_empty_selection_raises_rather_than_running_everything(self):
        with pytest.raises(ValueError, match="empty"):
            batch.parse_doc_ids(" , ")
        with pytest.raises(ValueError, match="empty"):
            batch.parse_doc_ids("")

    def test_a_missing_panel_file_raises(self, tmp_path):
        with pytest.raises(ValueError, match="not a file"):
            batch.parse_doc_ids(None, str(tmp_path / "absent.txt"))


class TestExpandCorpusAppliesThePanel:
    def test_the_panel_is_the_whole_selection_in_panel_order(self):
        ids = _ids()
        panel = [ids[2], ids[0]]
        docs, _, _ = batch.expand_corpus(_definitions(), 0, panel)
        assert [d["opaque_id"] for d in docs] == panel, (
            "a panel is a reading order: re-sorting it into corpus order "
            "reorders the verdict table under the reader"
        )

    def test_without_a_panel_the_corpus_is_whole(self):
        docs, _, _ = batch.expand_corpus(_definitions())
        assert len(docs) == len(_ids()) == 4

    def test_an_unknown_id_fails_loudly_and_names_itself(self):
        with pytest.raises(ValueError, match="ghost_id"):
            batch.expand_corpus(_definitions(), 0, ["ghost_id"])

    def test_an_id_filtered_by_max_chars_fails_loudly(self):
        ids = _ids()
        with pytest.raises(ValueError, match="not in the corpus"):
            batch.expand_corpus(_definitions(), 3, [ids[0]])


class TestBothArmsTakeTheSelection:
    """The wiring: each arm parses the flag and hands it to the same seam."""

    def test_the_batch_runner_passes_its_selection_on(self, monkeypatch):
        seen = {}

        def _spy(definitions, max_chars=0, doc_ids=None):
            seen["doc_ids"] = doc_ids
            return [], [], 0

        monkeypatch.setattr(batch, "expand_corpus", _spy)
        monkeypatch.setenv("TEXT_CONFIG_PASSPHRASE", "witness")
        monkeypatch.setattr(
            "argumentation_analysis.core.utils.crypto_utils.derive_encryption_key",
            lambda passphrase: b"key",
        )
        monkeypatch.setattr(
            "argumentation_analysis.core.io_manager.load_extract_definitions",
            lambda **kwargs: [],
        )
        assert batch.main(["--doc-ids", "a,b"]) == 0
        assert seen["doc_ids"] == ["a", "b"]

    def test_the_zeroshot_dry_run_lists_exactly_the_panel(self, monkeypatch, capsys):
        monkeypatch.setattr(arm, "load_definitions", _definitions)
        ids = _ids()
        panel = [ids[1], ids[3]]
        rc = asyncio.run(arm.run_arm(["--dry-run", "--doc-ids", ",".join(panel)]))
        assert rc == 0
        printed = capsys.readouterr().out
        listed = [
            line.split()[0]
            for line in printed.splitlines()
            if line.startswith("  ") and "chars=" in line
        ]
        assert listed == panel, (
            "the zero-shot dry-run must list the panel it would run, in "
            f"order — got {listed}"
        )
        assert "candidate documents: 2" in printed


class TestTheWitnessCarriesItsOwnSalt:
    """The CI red: my seat's ``.env`` lent ``OPAQUE_ID_SALT`` and the gate
    had none — the witnesses were green here and red there. They now run on
    a synthetic salt (autouse), and this class pins BOTH sides of that
    contract: hermetic here, loud in production without a secret."""

    def test_no_witness_borrows_the_seats_real_salt(self, monkeypatch):
        """The autouse salt is synthetic — a seat leaking the real one into
        the environment cannot change what the ids above are derived from."""
        monkeypatch.setenv("OPAQUE_ID_SALT", "real-seat-secret-that-must-not-win")
        assert opaque_id("src_one", salt=SALT) == _ids()[0]

    def test_the_salt_contract_refuses_loudly_when_no_salt_exists(self):
        """A child process with ``OPAQUE_ID_SALT`` stripped (the gate's
        condition) must see the salt contract REFUSE, not fall back to a
        public default (#1973).

        The child imports ``opaque_id`` **directly**, not by way of
        ``run_corpus_batch``: that module's import chain reaches a
        ``load_dotenv``, which on a seat re-borrows the very ``.env`` whose
        absence this witness is about — measured: a child running
        ``expand_corpus`` with the variable stripped exits 0 here, because
        the chain refills it. Isolating the function under contract is what
        makes the absence observable.
        """
        code = (
            "import sys; sys.path.insert(0, r'{root}'); "
            "from argumentation_analysis.evaluation.opaque_id import opaque_id; "
            "opaque_id('src_one')"
        ).format(root=REPO_ROOT)
        env = {k: v for k, v in os.environ.items() if k != "OPAQUE_ID_SALT"}
        assert "OPAQUE_ID_SALT" not in env, "the child must start saltless"
        proc = subprocess.run(
            [sys.executable, "-I", "-c", code],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(REPO_ROOT),
            timeout=120,
        )
        assert proc.returncode != 0, (
            "opaque_id must not succeed without a salt — it would mean a "
            "public default crept back in"
        )
        assert "OPAQUE_ID_SALT is required" in proc.stderr
