"""#2841 — guards for the reading-folder producer.

The reading folder is the campaign's metric-mandate deliverable: a human
reads the acts, not a report about them. Each guard kills an anti-pattern
the coordinator's dispatch (R1105) named:

1. writing the folder somewhere git tracks — it carries real corpus
   names (dataset privacy rule 4: the frontier is GitHub indexation);
2. a folder with holes — a signature without a full state dump would
   render a fiche with empty acts, silently;
3. a stripped render — the ZIP's signatures carry ``{'length': N,
   'stripped': True}`` placeholders; the readable text exists ONLY in
   the full state dumps and must land in the fiche verbatim;
4. numbers copied from a report — every table figure must be re-read
   from an artifact (counts, lengths) or recomputed from measured
   tokens (#3095 price table), never restated.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.dataset import render_campaign_reading_folder as folder

# Two designated ids + one undesignated: the reading order must number
# the designated documents first, in DESIGNATED_ORDER's order.
DOCS = {
    "a53fc485_ext0": {
        "title": "Titre Alpha",
        "speaker": "Locuteur A",
        "year": "1940",
        "raw_text": "x" * 1200,
        "args": ["a1", "a2", "a3"],
        "fallacies": ["f1"],
        "fol": [{"r": 1}],
        "answer": "Réponse zero-shot alpha, intégrale. " * 20,
    },
    "00b283cf_ext9": {
        "title": "Titre Beta",
        "speaker": "Locuteur B",
        "year": "1960",
        "raw_text": "y" * 3400,
        "args": ["b%d" % i for i in range(6013)],
        "fallacies": ["f1", "f2"],
        "fol": [],
        "answer": "Réponse zero-shot beta, intégrale. " * 20,
    },
    "zz_free_ext0": {
        "title": "Titre Gamma",
        "speaker": "Locuteur C",
        "year": "2000",
        "raw_text": "z" * 800,
        "args": ["g1"],
        "fallacies": [],
        "fol": [],
        "answer": "Réponse zero-shot gamma. " * 5,
    },
}


def _plant_campaign(tmp_path: Path) -> Path:
    """A synthetic 3-document campaign under tmp_path; returns its results root."""
    root = tmp_path / "results"
    sig_dir = tmp_path / "signatures"
    states_dir = tmp_path / "state_dumps"
    zs_dir = tmp_path / "zeroshot"
    for d in (root, sig_dir, states_dir, zs_dir):
        d.mkdir(parents=True)
    for doc_id, spec in DOCS.items():
        act = f"ACTE INTEGRAL de {doc_id}. " + "texte " * 120
        sig = {
            "opaque_id": doc_id,
            "metadata": {
                "title": spec["title"],
                "speaker": spec["speaker"],
                "date_or_year": spec["year"],
            },
            "workflow": "spectacular",
            "wall_clock_s": 12.5,
            "outcome": {"status": "ok"},
            # 2000 prompt + 1000 completion tokens on the haiku standard
            # row (0.10/0.50 $/MTok) = 0.0002 + 0.0005 = 0.0007 $ exactly.
            "llm_usage": {
                "act1_framing": {
                    "prompt_tokens": 2000,
                    "completion_tokens": 1000,
                    "calls": 1,
                }
            },
        }
        (sig_dir / f"signature_{doc_id}.json").write_text(
            json.dumps(sig, ensure_ascii=False), encoding="utf-8"
        )
        state = {
            "raw_text": spec["raw_text"],
            "identified_arguments": spec["args"],
            "identified_fallacies": spec["fallacies"],
            "fol_analysis_results": spec["fol"],
            "propositional_analysis_results": [],
            "modal_analysis_results": [],
            "act1_framing": act,
            "act2_narrative": act,
            "act3_conclusion": act,
            "narrative_synthesis": act,
            "interpretive_question": "Question ?",
            "reading_window_status": None,
            "restitution_acts_degraded": None,
        }
        (states_dir / f"state_full_{doc_id}.json").write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8"
        )
        zs = {
            "provenance": {
                "model": "claude-haiku-5-5",
                "git_head": "synthetic-head-2841",
                "max_chars": 0,
            },
            "opaque_id": doc_id,
            "chars_in": len(spec["raw_text"]),
            "elapsed_seconds": 3.2,
            "status_code": 200,
            "answer": spec["answer"],
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 500, "completion_tokens": 200},
        }
        (zs_dir / f"{doc_id}.json").write_text(
            json.dumps(zs, ensure_ascii=False), encoding="utf-8"
        )
    return root


def _run_producer(tmp_path: Path, monkeypatch) -> Path:
    root = _plant_campaign(tmp_path)
    out = root / "campaign_2841_lecture"
    monkeypatch.setattr(folder, "RESULTS_ROOT", root)
    rc = folder.main(
        [
            "--signatures-dir",
            str(tmp_path / "signatures"),
            "--states-dir",
            str(tmp_path / "state_dumps"),
            "--zeroshot-dir",
            str(tmp_path / "zeroshot"),
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    return out


class TestPathGuard:
    """The folder carries real corpus names: it never leaves the gitignored
    results tree (#2353 rule 1, dataset privacy rule 4)."""

    def test_refuses_to_write_outside_the_results_root(self, tmp_path, monkeypatch):
        _plant_campaign(tmp_path)
        monkeypatch.setattr(folder, "RESULTS_ROOT", tmp_path / "results")
        with pytest.raises(SystemExit, match="refusing to write outside"):
            folder.main(
                [
                    "--signatures-dir",
                    str(tmp_path / "signatures"),
                    "--states-dir",
                    str(tmp_path / "state_dumps"),
                    "--zeroshot-dir",
                    str(tmp_path / "zeroshot"),
                    "--out",
                    str(tmp_path / "elsewhere"),
                ]
            )
        assert not (tmp_path / "elsewhere").exists()

    def test_output_default_is_gitignored_in_the_repo(self):
        import subprocess

        rc = subprocess.run(
            ["git", "check-ignore", str(folder.DEFAULT_OUT)],
            capture_output=True,
            text=True,
            cwd=str(folder.REPO_ROOT),
        )
        assert rc.returncode == 0, (
            f"{folder.DEFAULT_OUT} is not gitignored — the reading folder "
            "must never leave the machine via git"
        )


class TestNoHoles:
    """A signature without its full state dump refuses the whole folder —
    a fiche with empty acts would read as 'the campaign produced nothing'."""

    def test_missing_state_dump_is_a_named_exit(self, tmp_path, monkeypatch):
        root = _plant_campaign(tmp_path)
        (root.parent / "state_dumps" / "state_full_zz_free_ext0.json").unlink()
        monkeypatch.setattr(folder, "RESULTS_ROOT", root)
        with pytest.raises(SystemExit, match="zz_free_ext0"):
            folder.main(
                [
                    "--signatures-dir",
                    str(tmp_path / "signatures"),
                    "--states-dir",
                    str(tmp_path / "state_dumps"),
                    "--zeroshot-dir",
                    str(tmp_path / "zeroshot"),
                    "--out",
                    str(root / "campaign_2841_lecture"),
                ]
            )


class TestFullActs:
    """The ZIP's signatures carry stripped placeholders; the fiche must carry
    the acts from the FULL state dump, verbatim."""

    def test_fiche_contains_the_act_text_not_the_placeholder(
        self, tmp_path, monkeypatch
    ):
        out = _run_producer(tmp_path, monkeypatch)
        fiche = out / "02_rendus" / "01_a53fc485_ext0_Titre-Alpha.md"
        text = fiche.read_text(encoding="utf-8")
        assert "ACTE INTEGRAL de a53fc485_ext0." in text
        assert "stripped" not in text, "a stripped placeholder leaked into the render"

    def test_fiche_carries_the_zeroshot_answer_verbatim(self, tmp_path, monkeypatch):
        out = _run_producer(tmp_path, monkeypatch)
        fiche = (out / "02_rendus" / "01_a53fc485_ext0_Titre-Alpha.md").read_text(
            encoding="utf-8"
        )
        assert DOCS["a53fc485_ext0"]["answer"] in fiche

    def test_fiche_opens_with_the_provenance_header(self, tmp_path, monkeypatch):
        out = _run_producer(tmp_path, monkeypatch)
        fiche = (out / "02_rendus" / "01_a53fc485_ext0_Titre-Alpha.md").read_text(
            encoding="utf-8"
        )
        assert fiche.startswith("---")
        assert "synthetic-head-2841" in fiche
        assert "claude-haiku-5-5" in fiche


class TestNumbersComeFromArtifacts:
    """Every figure is re-read from an artifact or recomputed from measured
    tokens — never copied from a report."""

    def test_table_row_carries_state_counts_and_recomputed_cost(
        self, tmp_path, monkeypatch
    ):
        out = _run_producer(tmp_path, monkeypatch)
        table = (out / "01_tableau_corpus.md").read_text(encoding="utf-8")
        # Length from len(raw_text), args from the state, cost from tokens
        # (0.0007 $ hand-computed on the haiku standard row).
        assert "| 1200 | 3 | 1 | 1/0/0 |" in table
        assert "0.0007 $" in table
        # The flood document is flagged against its measured count.
        assert "6013" in table

    def test_phase_aggregates_price_at_the_standard_row(self):
        """The signature records per-PHASE token sums, not per-call sizes: an
        aggregate past 100k must NOT bill at the long-prompt tier (measured on
        the campaign: 21.94 $ instead of 8.17 $) — no single call crossed the
        threshold, so the standard row applies."""
        usage = {
            "hierarchical_fallacy": {
                "prompt_tokens": 254_879,
                "completion_tokens": 24_759,
                "calls": 36,
            }
        }
        cost = folder.doc_cost_usd(usage)
        expected = round(254_879 / 1e6 * 0.10 + 24_759 / 1e6 * 0.50, 4)
        assert cost == expected  # 0.0379 $ — the long row would say 0.1893 $

    def test_inondation_table_measures_args_against_length(self, tmp_path, monkeypatch):
        out = _run_producer(tmp_path, monkeypatch)
        flood = (out / "inondation_extraction.md").read_text(encoding="utf-8")
        assert "`00b283cf_ext9` | 3400 | 6013 |" in flood

    def test_reading_order_numbers_the_designated_first(self, tmp_path, monkeypatch):
        out = _run_producer(tmp_path, monkeypatch)
        renders = sorted(p.name for p in (out / "02_rendus").glob("*.md"))
        assert renders[0].startswith("01_a53fc485_ext0")
        assert renders[1].startswith("02_00b283cf_ext9")
        assert renders[2].startswith("03_zz_free_ext0")

    def test_reconciliation_counts_survive(self, tmp_path, monkeypatch):
        out = _run_producer(tmp_path, monkeypatch)
        readme = (out / "00_LIRE_D_ABORD.md").read_text(encoding="utf-8")
        assert "3 documents" in readme or "3 segments" in readme
