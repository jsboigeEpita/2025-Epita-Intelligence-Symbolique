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
from typing import List

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
        # The REAL campaign states carry these collections as dicts
        # {arg_N: text} (measured on the anchor doc: 134 entries) — the
        # synthetic campaign must plant that shape, not lists: a list-only
        # counter passed every witness while zeroing the real render.
        "args": {"arg_1": "a", "arg_2": "b", "arg_3": "c"},
        "fallacies": {"fallacy_1": "f"},
        "fol": [{"r": 1}],
        "answer": "Réponse zero-shot alpha, intégrale. " * 20,
    },
    "00b283cf_ext9": {
        "title": "Titre Beta",
        "speaker": "Locuteur B",
        "year": "1960",
        "raw_text": "y" * 3400,
        "args": {f"arg_{i}": "b" for i in range(6013)},
        "fallacies": {"fallacy_1": "f1", "fallacy_2": "f2"},
        "fol": [],
        "answer": "Réponse zero-shot beta, intégrale. " * 20,
    },
    "zz_free_ext0": {
        "title": "Titre Gamma",
        "speaker": "Locuteur C",
        "year": "2000",
        "raw_text": "z" * 800,
        "args": {"arg_1": "g"},
        "fallacies": {},
        "fol": [],
        "answer": "Réponse zero-shot gamma. " * 5,
    },
}


def _plant_campaign(tmp_path: Path, model: str = "claude-haiku-5-5") -> Path:
    """A synthetic 3-document campaign under tmp_path; returns its results root.

    ``model`` lands in every zero-shot record's provenance — the ONLY place
    the run's pricing row exists (the default is the haiku campaign's)."""
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
                "model": model,
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
    # A decoy state from ANOTHER campaign: the states dir holds older runs'
    # dumps (90 files where this campaign has 49) and the annexes must not
    # absorb them.
    (states_dir / "state_full_decoy_old_campaign.json").write_text(
        json.dumps({"raw_text": "ancien"}), encoding="utf-8"
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


class TestAnnexesFilter:
    """The annexes carry THIS campaign's artifacts — the states dir also
    holds older campaigns' dumps and must not leak into the folder."""

    def test_annexes_states_carry_only_campaign_docs(self, tmp_path, monkeypatch):
        out = _run_producer(tmp_path, monkeypatch)
        states = sorted(p.name for p in (out / "04_annexes" / "states").glob("*.json"))
        assert len(states) == len(DOCS)
        assert not any("decoy" in name for name in states)
        for doc_id in DOCS:
            assert f"state_full_{doc_id}.json" in states


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


def _producer_argv(tmp_path: Path, out: Path) -> List[str]:
    return [
        "--signatures-dir",
        str(tmp_path / "signatures"),
        "--states-dir",
        str(tmp_path / "state_dumps"),
        "--zeroshot-dir",
        str(tmp_path / "zeroshot"),
        "--out",
        str(out),
    ]


class TestPricingFollowsTheRunsProvenance:
    """#3138 — the run's model prices every pipeline figure, and a provenance
    that names no model is a named exit.

    The first head of this producer priced every campaign at the module
    constant's haiku row: on a sonnet-tier campaign the recomputed pipeline
    total read 0.9314 $ where the campaign's own accountant had measured
    18.6255 $ — exactly the ratio of the two rows (x20). The run's model
    exists in exactly one place, the zero-shot records' provenance, so it is
    resolved there, BEFORE the first fact is built. Falling back silently to
    the constant is the shape that produced the x20, so every resolution is
    loud: no model, no pricing.
    """

    def test_a_sonnet_tier_is_priced_at_the_sonnet_row(self, tmp_path, monkeypatch):
        """A provenance naming claude-sonnet-5-5 prices the pipeline at the
        sonnet row: 2000 prompt + 1000 completion tokens per doc at 2/10
        $/MTok = 0.0140 $ (hand-computed), not the haiku row's 0.0007 $."""
        root = _plant_campaign(tmp_path, model="claude-sonnet-5-5")
        out = root / "campaign_2841_lecture"
        monkeypatch.setattr(folder, "RESULTS_ROOT", root)
        assert folder.main(_producer_argv(tmp_path, out)) == 0
        table = (out / "01_tableau_corpus.md").read_text(encoding="utf-8")
        assert "0.0140 $" in table
        assert "0.0007 $" not in table
        fiche = (out / "02_rendus" / "01_a53fc485_ext0_Titre-Alpha.md").read_text(
            encoding="utf-8"
        )
        assert "model: claude-sonnet-5-5" in fiche

    def test_doc_cost_usd_prices_the_model_it_is_given(self):
        """Unit contract: the pricing row follows the model argument. The
        default (the module constant) stays the haiku positive control —
        the end-to-end haiku control is the existing tableau witness's
        0.0007 $, which now reaches the table through the provenance."""
        usage = {
            "act1_framing": {
                "prompt_tokens": 2000,
                "completion_tokens": 1000,
                "calls": 1,
            }
        }
        expected_sonnet = round(2000 / 1e6 * 2.00 + 1000 / 1e6 * 10.00, 4)
        expected_haiku = round(2000 / 1e6 * 0.10 + 1000 / 1e6 * 0.50, 4)
        assert folder.doc_cost_usd(usage, pricing_model="claude-sonnet-5-5") == (
            expected_sonnet  # 0.014 $ — the x20 of the haiku figure
        )
        assert folder.doc_cost_usd(usage) == expected_haiku  # 0.0007 $

    def test_the_readme_standard_figure_prices_the_runs_model(
        self, tmp_path, monkeypatch
    ):
        """The readme's zero-shot standard figure used the haiku row in hard
        (0.10/0.50) — the same x20 on a sonnet run. 3 docs x (500 prompt +
        200 completion) at 2/10 $/MTok = 0.0090 $."""
        root = _plant_campaign(tmp_path, model="claude-sonnet-5-5")
        out = root / "campaign_2841_lecture"
        monkeypatch.setattr(folder, "RESULTS_ROOT", root)
        assert folder.main(_producer_argv(tmp_path, out)) == 0
        readme = (out / "00_LIRE_D_ABORD.md").read_text(encoding="utf-8")
        assert "0.0090 $** au tarif standard" in readme

    def test_a_provenance_without_a_model_is_a_named_exit(self, tmp_path, monkeypatch):
        """No record names a model: the pricing row cannot be guessed, and
        the producer says so instead of pricing at the constant."""
        root = _plant_campaign(tmp_path)
        for p in (tmp_path / "zeroshot").glob("*.json"):
            record = json.loads(p.read_text(encoding="utf-8"))
            del record["provenance"]["model"]
            p.write_text(json.dumps(record), encoding="utf-8")
        monkeypatch.setattr(folder, "RESULTS_ROOT", root)
        with pytest.raises(SystemExit, match="no provenance model"):
            folder.main(_producer_argv(tmp_path, root / "campaign_2841_lecture"))

    def test_a_later_record_without_a_model_is_a_named_exit(
        self, tmp_path, monkeypatch
    ):
        """The run resolves its model from the first record, but EACH record
        prices its own zero-shot cost: one that names no model exits when
        its fiche is rendered, by its own id."""
        root = _plant_campaign(tmp_path)
        target = tmp_path / "zeroshot" / "zz_free_ext0.json"
        record = json.loads(target.read_text(encoding="utf-8"))
        del record["provenance"]["model"]
        target.write_text(json.dumps(record), encoding="utf-8")
        monkeypatch.setattr(folder, "RESULTS_ROOT", root)
        with pytest.raises(SystemExit, match="zz_free_ext0"):
            folder.main(_producer_argv(tmp_path, root / "campaign_2841_lecture"))

    def test_no_zeroshot_arm_is_a_named_exit(self, tmp_path, monkeypatch):
        """No zero-shot record at all: there is no provenance to read the
        model from, so the pricing stamp could not be written honestly."""
        root = _plant_campaign(tmp_path)
        for p in (tmp_path / "zeroshot").glob("*.json"):
            p.unlink()
        monkeypatch.setattr(folder, "RESULTS_ROOT", root)
        with pytest.raises(SystemExit, match="no zero-shot record"):
            folder.main(_producer_argv(tmp_path, root / "campaign_2841_lecture"))
