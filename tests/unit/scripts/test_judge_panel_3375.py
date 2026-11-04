"""#3375 — the v1 panel's blind judge, witnessed without a paid call.

The dispatch's DoD, one witness per clause:

- a fake judge with a deterministic seed;
- a same-family judge is refused;
- an invented citation drops the item **and it is counted**;
- the dry-run lists exactly the panel;
- the verdict table is produced on synthetic arm outputs.

Tranche 3 (R1140): the judge reads the SOURCE DOCUMENT (third prompt block,
decrypted in memory, never persisted) and verifies ``document_quote``
mechanically against it; the judged pipeline text IS the fiche's full-text
section — one producer, two callers — so a non-argumentative document shows
the judge its terminal classification instead of an empty string.

Plus the shapes that would make the instrument lie quietly: an unparsed
answer coerced into a verdict, an M1 unprovable by construction, a cost
printed as 0.0000 $ because the model is not priced (#1019 tri-state), a
table built on a subset of the panel and reported as the panel.

No network, no dataset, no key: every call goes through the injected
``judge_call``, the endpoint resolver and the document loader are replaced.
**Zero paid call, zero corpus read.**
"""

from __future__ import annotations

import asyncio
import json
import random
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from scripts.dataset import judge_panel as jp  # noqa: E402

# --- synthetic arms -------------------------------------------------------
# Deliberately unlike the corpus: no real name, no real excerpt. What matters
# is that a quote can be found (or not) mechanically.
PIPELINE_TEXT = (
    "Acte I — cadrage. Le graphe rejette la these alpha dans la semantique "
    "stable et l'accepte dans la semantique preferee ; aucun argument ne "
    "survit aux deux."
)
ZEROSHOT_TEXT = (
    "Le document defend la these beta en s'appuyant sur un exemple date, et "
    "ne discute jamais la semantique preferee."
)
DOCUMENT_TEXT = (
    "Discours synthetique de test. La these centrale affirme que la mesure "
    "de 1998 a reduit le deficit de moitie, et le texte appuie cette "
    "affirmation sur trois chiffres dates."
)
DOC_QUOTE = "la mesure de 1998 a reduit le deficit de moitie"
GAP_TEXT = "la semantique preferee"  # present in the reading, absent from the analysis

PANEL = ["aaaa1111", "bbbb2222", "cccc3333"]
SEED = 3375


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def make_world(tmp_path: Path, ids=PANEL, zeroshot_model="gpt-5.6-luna"):
    """A tiny stand-in for the campaign: both arms, on synthetic text."""
    states = tmp_path / "states"
    signatures = tmp_path / "signatures"
    zeroshots = tmp_path / "zeroshots"
    for doc_id in ids:
        _write_json(
            states / f"state_full_{doc_id}.json",
            {
                "state": {
                    "act1_framing": PIPELINE_TEXT,
                    "interpretive_question": "Quelle premisse reste sans appui ?",
                }
            },
        )
        _write_json(
            signatures / f"signature_{doc_id}.json",
            {
                "opaque_id": doc_id,
                "llm_usage": {
                    "phase_1": {"prompt_tokens": 1200, "completion_tokens": 300}
                },
            },
        )
        _write_json(
            zeroshots / f"{doc_id}.json",
            {
                "opaque_id": doc_id,
                "provenance": {"model": zeroshot_model, "git_head": "deadbeef"},
                "usage": {"prompt_tokens": 900, "completion_tokens": 250},
                "answer": ZEROSHOT_TEXT,
            },
        )
    return {
        "states": states,
        "signatures": signatures,
        "zeroshots": zeroshots,
        "out": tmp_path / "out",
    }


def _answer(
    state="PIPELINE_SUPPLIES",
    items=None,
    identification="1",
    conclusion="Le surplus est formel.",
):
    return json.dumps(
        {
            "identification": identification,
            "state": state,
            "items": items or [],
            "style_notes": ["l'analyse est plus longue"],
            "conclusion": conclusion,
        },
        ensure_ascii=False,
    )


class FakeJudge:
    """Counts its calls and answers from a fixed table — never the network."""

    def __init__(self, answer=None):
        self.calls = []
        self._answer = answer or (lambda doc, prompt: _answer())

    async def __call__(self, endpoint, prompt, timeout=600):
        self.calls.append(prompt)
        return {
            "status_code": 200,
            "answer": self._answer(None, prompt),
            "prompt_tokens": 2000,
            "completion_tokens": 400,
            "usage": {},
        }


def _argv(world, judge_model="claude-sonnet-5-5", extra=()):
    return [
        "--judge-model",
        judge_model,
        "--panel-file",
        str(world["panel_file"]),
        "--seed",
        str(SEED),
        "--states-dir",
        str(world["states"]),
        "--signatures-dir",
        str(world["signatures"]),
        "--zeroshot-dir",
        str(world["zeroshots"]),
        "--out-dir",
        str(world["out"]),
        *extra,
    ]


def _with_panel_file(world, ids=PANEL):
    panel_file = world["states"].parent / "panel.txt"
    panel_file.write_text("\n".join(ids) + "\n", encoding="utf-8")
    return {**world, "panel_file": panel_file}


@pytest.fixture(autouse=True)
def _no_named_route(monkeypatch):
    """The judge's route is replaced: a witness must never need a real key."""
    monkeypatch.setattr(
        jp,
        "resolve_judge_endpoint",
        lambda model: {
            "api_key": "not-a-key",
            "base_url": "https://example.invalid/v1",
            "model_id": model,
            "family": "anthropic",
            "host": "example.invalid",
            "route": "test",
        },
    )


@pytest.fixture(autouse=True)
def _synthetic_documents(monkeypatch):
    """The document loader is replaced: no witness ever reads the corpus.

    The real loader decrypts the encrypted dataset in memory (privacy rule 5)
    — a test touching it would put source text in test output. Every witness
    judges a synthetic document instead.
    """
    monkeypatch.setattr(
        jp,
        "load_document_texts",
        lambda panel: {doc_id: DOCUMENT_TEXT for doc_id in panel},
    )


# ---------------------------------------------------------------------------
# The draw
# ---------------------------------------------------------------------------


class TestTheDraw:
    def test_same_seed_and_document_always_give_the_same_order(self):
        first = [jp.draw_order(doc, SEED) for doc in PANEL]
        second = [jp.draw_order(doc, SEED) for doc in PANEL]
        assert first == second

    def test_the_order_is_drawn_per_document_not_once_for_the_panel(self):
        """A single global order lets a position bias dress up as an effect."""
        draws = {jp.draw_order(f"doc{i:04d}", SEED) for i in range(64)}
        assert draws == {
            True,
            False,
        }, "every document fell on the same side: the draw is not per document"

    def test_positions_are_a_permutation_of_one_and_two(self):
        for doc in PANEL:
            pos = jp.positions(doc, SEED)
            assert pos["pipeline"] in (1, 2)
            assert pos["zeroshot"] in (1, 2)
            assert pos["pipeline"] != pos["zeroshot"]

    def test_positions_match_the_draw(self):
        """The permutation is the draw's, checked against the stdlib directly."""
        for doc in PANEL:
            expected = random.Random(f"{SEED}:{doc}").random() < 0.5
            assert jp.draw_order(doc, SEED) is expected

    def test_a_different_seed_can_change_the_order(self):
        """A seed that changes nothing is a seed that is not read."""
        for doc in PANEL:
            other = jp.draw_order(doc, SEED + 1)
            if other != jp.draw_order(doc, SEED):
                return
        pytest.fail("no document changed side across two seeds — the seed is not read")


# ---------------------------------------------------------------------------
# Why the judge must be another family
# ---------------------------------------------------------------------------


class TestTheJuryIsNotTheAuthor:
    def test_same_family_is_refused_with_both_ids_named(self):
        with pytest.raises(ValueError) as excinfo:
            jp.assert_judge_differs("gpt-5.6-luna", "gpt-5.6-luna")
        message = str(excinfo.value)
        assert "gpt-5.6-luna" in message
        assert "same" in message.lower() or "both" in message.lower()

    def test_another_family_passes_and_returns_both_families(self):
        assert jp.assert_judge_differs("claude-sonnet-5-5", "gpt-5.6-luna") == (
            "anthropic",
            "openai",
        )

    def test_an_unknown_family_raises_instead_of_being_guessed(self):
        with pytest.raises(ValueError):
            jp.model_family("a-model-nobody-priced")

    def test_a_longer_prefix_wins_over_its_own_shorter_prefix(self, monkeypatch):
        """Longest-first is the MATCH's rule, not the table's declaration order.

        A vendor row added above its own extension (``x-`` before ``x-long-``)
        must not shadow it — the comment said so before the code did (R1140).
        """
        import argumentation_analysis.evaluation.model_family as mf

        monkeypatch.setattr(
            mf,
            "_FAMILY_PREFIXES",
            (("x-", "family_a"), ("x-long-", "family_b")),
        )
        assert mf.model_family("x-long-1") == "family_b"
        assert mf.model_family("x-other-1") == "family_a"

    def test_the_runner_refuses_before_any_call(self, tmp_path):
        """The refusal is a stop, not a warning printed next to a running pass."""
        world = _with_panel_file(make_world(tmp_path))
        judge = FakeJudge()
        with pytest.raises(ValueError):
            asyncio.run(
                jp.run(
                    _argv(world, judge_model="gpt-5.6-luna", extra=("--dry-run",)),
                    judge_call=judge,
                )
            )
        assert judge.calls == []


# ---------------------------------------------------------------------------
# Citations: an item without a findable quote does not exist
# ---------------------------------------------------------------------------


class TestCitations:
    def test_an_invented_citation_drops_the_item_and_is_counted(self):
        kept, dropped = jp.validate_items(
            [
                {
                    "code": "S2",
                    "analysis_quote": "un argument que le document ne contient nulle part",
                    "note": "inventé",
                }
            ],
            PIPELINE_TEXT,
            ZEROSHOT_TEXT,
            DOCUMENT_TEXT,
        )
        assert kept == []
        assert len(dropped) == 1
        assert dropped[0]["code"] == "S2"
        assert dropped[0]["reason"] == "quote_not_in_pipeline_text"

    def test_a_real_citation_survives(self):
        """The control: the same item with a true quote is KEPT.

        Without it, the drop witness would pass on an instrument that drops
        everything.
        """
        kept, dropped = jp.validate_items(
            [
                {
                    "code": "S2",
                    "analysis_quote": "l'accepte dans la semantique preferee",
                }
            ],
            PIPELINE_TEXT,
            ZEROSHOT_TEXT,
            DOCUMENT_TEXT,
        )
        assert dropped == []
        assert len(kept) == 1
        assert kept[0]["code"] == "S2"

    def test_whitespace_and_line_wrapping_do_not_break_a_citation(self):
        wrapped = PIPELINE_TEXT.replace(" ", "\n   ", 3)
        assert jp.is_cited(wrapped, "l'accepte dans la semantique preferee")

    def test_a_paraphrase_is_not_a_citation(self):
        assert not jp.is_cited(
            PIPELINE_TEXT, "le graphe accepte la these alpha dans la semantique stable"
        )

    def test_a_bare_keyword_is_not_a_citation(self):
        """It occurs in every text, so it proves nothing about this one."""
        assert not jp.is_cited(PIPELINE_TEXT, "alpha")

    def test_a_quote_from_the_wrong_side_drops_the_item(self):
        kept, dropped = jp.validate_items(
            [{"code": "S1", "analysis_quote": ZEROSHOT_TEXT}],
            PIPELINE_TEXT,
            ZEROSHOT_TEXT,
            DOCUMENT_TEXT,
        )
        assert kept == []
        assert dropped[0]["reason"] == "quote_not_in_pipeline_text"

    def test_an_m1_needs_only_the_reading_quote(self):
        """An M1 is an ABSENCE: demanding an analysis quote makes it unprovable."""
        kept, dropped = jp.validate_items(
            [
                {
                    "code": "M1",
                    "reading_quote": "ne discute jamais la semantique preferee",
                    "on_central_thesis": True,
                }
            ],
            PIPELINE_TEXT,
            ZEROSHOT_TEXT,
            DOCUMENT_TEXT,
        )
        assert dropped == []
        assert kept[0]["code"] == "M1"

    def test_an_m1_with_no_reading_quote_is_dropped(self):
        kept, dropped = jp.validate_items(
            [{"code": "M1", "analysis_quote": "Le graphe rejette la these alpha"}],
            PIPELINE_TEXT,
            ZEROSHOT_TEXT,
            DOCUMENT_TEXT,
        )
        assert kept == []
        assert dropped[0]["reason"] == "missing_zeroshot_quote"

    def test_an_m2_quotes_all_three_sides(self):
        kept, dropped = jp.validate_items(
            [
                {
                    "code": "M2",
                    "analysis_quote": "Le graphe rejette la these alpha",
                    "reading_quote": "Le document defend la these beta",
                    "document_quote": DOC_QUOTE,
                }
            ],
            PIPELINE_TEXT,
            ZEROSHOT_TEXT,
            DOCUMENT_TEXT,
        )
        assert dropped == []
        assert kept[0]["code"] == "M2"
        assert kept[0]["document_quote"] == DOC_QUOTE

    def test_an_unknown_code_is_dropped_not_kept_under_another_name(self):
        kept, dropped = jp.validate_items(
            [{"code": "S9", "analysis_quote": PIPELINE_TEXT}],
            PIPELINE_TEXT,
            ZEROSHOT_TEXT,
            DOCUMENT_TEXT,
        )
        assert kept == []
        assert dropped[0]["reason"] == "unknown_code"


# ---------------------------------------------------------------------------
# Severity is the runner's rule, not the judge's opinion
# ---------------------------------------------------------------------------


class TestSeverity:
    def test_m2_is_always_severe(self):
        assert jp.severity_of("M2") == "severe"
        assert jp.severity_of("M2", on_central_thesis=False) == "severe"

    def test_m1_on_the_central_thesis_is_severe(self):
        assert jp.severity_of("M1", on_central_thesis=True) == "severe"

    def test_m1_elsewhere_is_moderate(self):
        assert jp.severity_of("M1", on_central_thesis=False) == "moderate"

    def test_a_supply_has_no_severity(self):
        for code in ("S1", "S2", "S3", "S4", "S5"):
            assert jp.severity_of(code) is None


# ---------------------------------------------------------------------------
# The judge's answer
# ---------------------------------------------------------------------------


class TestTheAnswer:
    def test_bare_json_parses(self):
        assert jp.parse_judge_answer('{"state":"PARITY"}')["state"] == "PARITY"

    def test_json_wrapped_in_prose_parses(self):
        answer = 'Voici mon verdict.\n```json\n{"state":"PARITY"}\n```\nFin.'
        assert jp.parse_judge_answer(answer)["state"] == "PARITY"

    def test_nested_objects_do_not_truncate_the_parse(self):
        answer = '{"state":"PARITY","items":[{"code":"S1"}]}'
        parsed = jp.parse_judge_answer(answer)
        assert parsed["items"] == [{"code": "S1"}]

    def test_an_unreadable_answer_is_counted_not_coerced(self):
        row = jp._judge_one(
            "doc0", PIPELINE_TEXT, ZEROSHOT_TEXT, DOCUMENT_TEXT, SEED, "je ne sais pas"
        )
        assert row["state"] == "UNPARSED"
        assert row["kept"] == []
        assert row["dropped"][0]["code"] is None

    def test_an_unknown_state_is_not_silently_mapped_to_parity(self):
        row = jp._judge_one(
            "doc0",
            PIPELINE_TEXT,
            ZEROSHOT_TEXT,
            DOCUMENT_TEXT,
            SEED,
            _answer(state="PROBABLY_FINE"),
        )
        assert row["state"] == "UNPARSED"

    def test_the_identification_is_compared_with_the_draw(self):
        doc = PANEL[0]
        drawn_first = jp.positions(doc, SEED)["pipeline"] == 1
        row_one = jp._judge_one(
            doc,
            PIPELINE_TEXT,
            ZEROSHOT_TEXT,
            DOCUMENT_TEXT,
            SEED,
            _answer(identification="1"),
        )
        row_two = jp._judge_one(
            doc,
            PIPELINE_TEXT,
            ZEROSHOT_TEXT,
            DOCUMENT_TEXT,
            SEED,
            _answer(identification="2"),
        )
        assert row_one["identification_ok"] is drawn_first
        assert row_two["identification_ok"] is (not drawn_first)


# ---------------------------------------------------------------------------
# The prompt
# ---------------------------------------------------------------------------


class TestThePrompt:
    def test_no_arm_label_is_used(self):
        prompt = jp.build_judge_prompt(ZEROSHOT_TEXT, PIPELINE_TEXT, DOCUMENT_TEXT)
        assert "zeroshot_2841" not in prompt
        assert "zero-shot" not in prompt.lower()

    def test_the_prompt_never_says_which_position_is_which(self):
        prompt = jp.build_judge_prompt(ZEROSHOT_TEXT, PIPELINE_TEXT, DOCUMENT_TEXT)
        assert "Texte 1 est" not in prompt
        assert "Texte 2 est" not in prompt
        assert prompt.count("## Texte 1") == 1
        assert prompt.count("## Texte 2") == 1

    def test_both_texts_are_carried_verbatim(self):
        prompt = jp.build_judge_prompt(ZEROSHOT_TEXT, PIPELINE_TEXT, DOCUMENT_TEXT)
        assert ZEROSHOT_TEXT in prompt
        assert PIPELINE_TEXT in prompt

    def test_the_roles_are_described_so_the_codes_are_answerable(self):
        prompt = jp.build_judge_prompt(ZEROSHOT_TEXT, PIPELINE_TEXT, DOCUMENT_TEXT)
        assert "analyse multi-méthodes" in prompt
        assert "lecture en un seul passage" in prompt

    def test_the_citation_rule_is_stated(self):
        prompt = jp.build_judge_prompt(ZEROSHOT_TEXT, PIPELINE_TEXT, DOCUMENT_TEXT)
        assert "mot pour mot" in prompt

    def test_style_is_explicitly_not_a_gap(self):
        prompt = jp.build_judge_prompt(ZEROSHOT_TEXT, PIPELINE_TEXT, DOCUMENT_TEXT)
        assert "forme" in prompt and "pas un M" in prompt

    def test_the_texts_land_in_the_drawn_order(self):
        doc = PANEL[0]
        pos = jp.positions(doc, SEED)
        prompt = jp.build_judge_prompt(
            *(
                (PIPELINE_TEXT, ZEROSHOT_TEXT)
                if pos["pipeline"] == 1
                else (ZEROSHOT_TEXT, PIPELINE_TEXT)
            ),
            DOCUMENT_TEXT,
        )
        first_body = PIPELINE_TEXT if pos["pipeline"] == 1 else ZEROSHOT_TEXT
        assert prompt.index(first_body) < prompt.index(
            ZEROSHOT_TEXT if pos["pipeline"] == 1 else PIPELINE_TEXT
        )


# ---------------------------------------------------------------------------
# The source document — a third block, quoted by its own field
# ---------------------------------------------------------------------------


class TestTheDocument:
    def test_the_document_block_rides_in_the_prompt(self):
        """Without the source, the single-pass reading is the oracle of the
        M2s it itself produced — the judge must read what is contradicted."""
        prompt = jp.build_judge_prompt(PIPELINE_TEXT, ZEROSHOT_TEXT, DOCUMENT_TEXT)
        assert prompt.count("## Document") == 1
        assert DOCUMENT_TEXT in prompt

    def test_the_document_is_not_a_third_contender(self):
        """The document is the source, not a third analysis: exactly two
        numbered texts, and the M2 rule names the document line."""
        prompt = jp.build_judge_prompt(PIPELINE_TEXT, ZEROSHOT_TEXT, DOCUMENT_TEXT)
        assert prompt.count("## Texte 1") == 1
        assert prompt.count("## Texte 2") == 1
        assert "document_quote" in prompt

    def test_a_fabricated_document_quote_drops_the_item(self):
        kept, dropped = jp.validate_items(
            [
                {
                    "code": "M2",
                    "analysis_quote": "Le graphe rejette la these alpha",
                    "reading_quote": "Le document defend la these beta",
                    "document_quote": "une ligne que le document n'a jamais portee",
                }
            ],
            PIPELINE_TEXT,
            ZEROSHOT_TEXT,
            DOCUMENT_TEXT,
        )
        assert kept == []
        assert dropped[0]["reason"] == "quote_not_in_document_text"

    def test_an_m2_without_a_document_quote_is_dropped(self):
        """An M2 the source cannot be shown to contradict is an opinion."""
        kept, dropped = jp.validate_items(
            [
                {
                    "code": "M2",
                    "analysis_quote": "Le graphe rejette la these alpha",
                    "reading_quote": "Le document defend la these beta",
                }
            ],
            PIPELINE_TEXT,
            ZEROSHOT_TEXT,
            DOCUMENT_TEXT,
        )
        assert kept == []
        assert dropped[0]["reason"] == "missing_document_quote"

    def test_a_true_m2_with_its_document_line_survives(self):
        kept, dropped = jp.validate_items(
            [
                {
                    "code": "M2",
                    "analysis_quote": "Le graphe rejette la these alpha",
                    "reading_quote": "Le document defend la these beta",
                    "document_quote": DOC_QUOTE,
                }
            ],
            PIPELINE_TEXT,
            ZEROSHOT_TEXT,
            DOCUMENT_TEXT,
        )
        assert dropped == []
        assert kept[0]["code"] == "M2"
        assert kept[0]["document_quote"] == DOC_QUOTE

    def test_a_fabricated_document_quote_drops_even_a_code_that_does_not_require_one(
        self,
    ):
        """Required only for M2, VERIFIED wherever present: an invented
        citation is an invented citation, whatever code carries it."""
        kept, dropped = jp.validate_items(
            [
                {
                    "code": "S2",
                    "analysis_quote": "l'accepte dans la semantique preferee",
                    "document_quote": "le deficit a triple en 2004",
                }
            ],
            PIPELINE_TEXT,
            ZEROSHOT_TEXT,
            DOCUMENT_TEXT,
        )
        assert kept == []
        assert dropped[0]["reason"] == "quote_not_in_document_text"

    def test_an_s_item_with_a_true_document_quote_keeps_it(self):
        """Accepted for S*: the quote strengthens the item and is recorded."""
        kept, dropped = jp.validate_items(
            [
                {
                    "code": "S2",
                    "analysis_quote": "l'accepte dans la semantique preferee",
                    "document_quote": DOC_QUOTE,
                }
            ],
            PIPELINE_TEXT,
            ZEROSHOT_TEXT,
            DOCUMENT_TEXT,
        )
        assert dropped == []
        assert kept[0]["document_quote"] == DOC_QUOTE


# ---------------------------------------------------------------------------
# The judged text IS the fiche's text — one producer, two callers
# ---------------------------------------------------------------------------


def _facts(opaque_id, classification=None, outcome=None):
    """The fiche's facts dict, minimal but complete for render_fiche."""
    return {
        "title": "Titre synthetique",
        "speaker": "Orateur synthetique",
        "year": "2001",
        "opaque_id": opaque_id,
        "workflow": "standard",
        "status": "ok",
        "chars": 300,
        "args": 2,
        "fallacies": 1,
        "fol": 3,
        "pl": 1,
        "modal": 0,
        "wall_s": 12.0,
        "calls": 5,
        "cost": 0.0123,
        "reading_window_status": None,
        "restitution_acts_degraded": None,
        "classification": classification,
        "outcome": outcome or {},
    }


class TestTheJudgedTextIsTheFiche:
    def _fiche_section(self, tmp_path, state, signature, facts):
        from scripts.dataset import render_campaign_reading_folder as rcr

        zeroshot = {
            "answer": ZEROSHOT_TEXT,
            "elapsed_seconds": 4,
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "provenance": {"model": "gpt-5.6-luna", "git_head": "deadbeef"},
        }
        fiche = rcr.render_fiche(
            facts, state, zeroshot, "deadbeef", "gpt-5.6-luna", "cmd"
        )
        head = "## Le pipeline, en texte intégral\n\n"
        tail = "\n## La réponse zero-shot, intégrale"
        start = fiche.index(head) + len(head)
        return fiche[start : fiche.index(tail)]

    def test_the_judged_text_is_what_the_fiche_prints(self, tmp_path):
        """The judge reads the SAME string the reader reads — headings,
        placeholders and all. A second copy diverges (that is how the
        non-argumentative document reached the judge empty)."""
        state = {
            "state": {
                "act1_framing": PIPELINE_TEXT,
                "interpretive_question": "Quelle premisse reste sans appui ?",
            }
        }
        signature = {"opaque_id": "aaaa1111"}
        section = self._fiche_section(tmp_path, state, signature, _facts("aaaa1111"))
        assert section == jp.pipeline_text_from_state(state, signature)
        # and the section really carries the fiche's shapes, not bare blocks
        assert "### Acte I — cadrage" in section
        assert "*(absent de l'état" in section  # act II missing → placeholder

    def test_a_non_argumentative_document_is_not_judged_as_an_empty_text(
        self, tmp_path
    ):
        """#3278: the terminal classification is a READER-facing sentence —
        the judge that does not see it cannot even see why there is nothing.

        #3392: the reader's sentence is the French paragraph built from the
        recorded material. The batch runner's English line left the reader's
        surface (and with it the judge's text); it stays in the log.
        """
        state = {"state": {"act1_framing": "", "raw_text": "x" * 300}}
        signature = {
            "opaque_id": "aaaa1111",
            "document_classification": "non_argumentative",
            "outcome": {"status": "non_argumentative", "phase": "extraction"},
        }
        judged = jp.pipeline_text_from_state(state, signature)
        assert (
            judged.strip()
        ), "the judged text of a non-argumentative document is EMPTY"
        assert "non-argumentatif" in judged
        assert "n'a pas été lu comme une argumentation" in judged
        assert "classified non-argumentative" not in judged

    def test_the_non_argumentative_fiche_section_is_the_judged_text(self, tmp_path):
        state = {"state": {"act1_framing": "", "raw_text": "x" * 300}}
        signature = {
            "opaque_id": "aaaa1111",
            "document_classification": "non_argumentative",
            "outcome": {"status": "non_argumentative", "phase": "extraction"},
        }
        section = self._fiche_section(
            tmp_path,
            state,
            signature,
            _facts("aaaa1111", "non_argumentative", signature["outcome"]),
        )
        assert section == jp.pipeline_text_from_state(state, signature)


# ---------------------------------------------------------------------------
# The document loader — decrypted in memory, never persisted, whole
# ---------------------------------------------------------------------------


class TestTheDocumentLoader:
    def test_definitions_map_to_whole_texts_under_their_opaque_id(self, monkeypatch):
        monkeypatch.setenv("OPAQUE_ID_SALT", "test-salt-3375")
        from argumentation_analysis.evaluation.opaque_id import opaque_id as _oid

        doc_id = _oid("Source synthetique")
        definitions = [
            {
                "source_name": "Source synthetique",
                "extracts": [{"extract_text": DOCUMENT_TEXT}],
            }
        ]
        texts = jp.document_texts_from_definitions(definitions, [doc_id])
        assert texts[doc_id] == DOCUMENT_TEXT

    def test_the_run_stops_when_the_corpus_does_not_carry_a_panel_document(
        self, tmp_path
    ):
        """The judge rules on documents it can read — a panel id with no
        corpus text is a stop naming it, never a silent skip."""
        world = _with_panel_file(make_world(tmp_path))
        with pytest.raises(SystemExit) as excinfo:
            asyncio.run(
                jp.run(
                    _argv(world, extra=("--dry-run",)),
                    judge_call=FakeJudge(),
                    document_loader=lambda panel: {
                        doc_id: DOCUMENT_TEXT for doc_id in list(panel)[:-1]
                    },
                )
            )
        assert PANEL[-1] in str(excinfo.value)

    def test_no_passphrase_stops_the_run_before_any_corpus_read(self, monkeypatch):
        """Privacy rule 5 cuts both ways: no key, no document — and no
        fallback to judging without the source."""
        monkeypatch.delenv("TEXT_CONFIG_PASSPHRASE", raising=False)
        monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)
        with pytest.raises(SystemExit) as excinfo:
            jp._passphrase_or_exit()
        assert "TEXT_CONFIG_PASSPHRASE" in str(excinfo.value)


# ---------------------------------------------------------------------------
# The dry-run — the panel, the sizes, the cost, and no call
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_it_lists_exactly_the_panel(self, tmp_path, capsys):
        world = _with_panel_file(make_world(tmp_path))
        judge = FakeJudge()
        assert (
            asyncio.run(jp.run(_argv(world, extra=("--dry-run",)), judge_call=judge))
            == 0
        )
        out = capsys.readouterr().out
        for doc in PANEL:
            assert doc in out
        assert "not-in-the-panel" not in out
        assert f"candidate documents: {len(PANEL)}" in out
        assert judge.calls == [], "the dry-run made a call"
        assert "no call made" in out

    def test_it_prints_an_estimate_and_never_a_made_up_zero(self, tmp_path, capsys):
        world = _with_panel_file(make_world(tmp_path))
        asyncio.run(jp.run(_argv(world, extra=("--dry-run",)), judge_call=FakeJudge()))
        out = capsys.readouterr().out
        assert "estimated judge cost:" in out
        assert "unpriced" in out or "$" in out

    def test_an_unpriced_judge_says_unpriced(self, tmp_path, capsys):
        world = _with_panel_file(make_world(tmp_path))
        asyncio.run(
            jp.run(
                _argv(world, judge_model="claude-unpriced-9", extra=("--dry-run",)),
                judge_call=FakeJudge(),
            )
        )
        out = capsys.readouterr().out
        assert "unpriced" in out
        assert "0.0000 $" not in out

    def test_the_dry_run_prints_the_document_size_too(self, tmp_path, capsys):
        """The document rides in every prompt: its size is the number that
        decides whether the prompt fits the judge's context — printed BEFORE
        any call, so an oversize document is visible without paying for it."""
        world = _with_panel_file(make_world(tmp_path))
        asyncio.run(jp.run(_argv(world, extra=("--dry-run",)), judge_call=FakeJudge()))
        out = capsys.readouterr().out
        assert "document=" in out

    def test_a_panel_document_without_an_arm_stops_the_run(self, tmp_path):
        world = _with_panel_file(
            make_world(tmp_path, ids=PANEL[:2]), ids=PANEL + ["dddd4444"]
        )
        with pytest.raises(SystemExit) as excinfo:
            asyncio.run(
                jp.run(_argv(world, extra=("--dry-run",)), judge_call=FakeJudge())
            )
        assert "dddd4444" in str(excinfo.value)

    def test_no_panel_at_all_is_refused(self, tmp_path):
        world = make_world(tmp_path)
        world["panel_file"] = None
        argv = [
            "--judge-model",
            "claude-sonnet-5-5",
            "--states-dir",
            str(world["states"]),
            "--signatures-dir",
            str(world["signatures"]),
            "--zeroshot-dir",
            str(world["zeroshots"]),
            "--out-dir",
            str(world["out"]),
            "--dry-run",
        ]
        with pytest.raises(SystemExit):
            asyncio.run(jp.run(argv, judge_call=FakeJudge()))


# ---------------------------------------------------------------------------
# The table, on synthetic arms
# ---------------------------------------------------------------------------


class TestTheTable:
    def _run(self, world, judge):
        return asyncio.run(jp.run(_argv(world), judge_call=judge))

    def test_the_table_is_written_and_names_the_facts_it_was_given(self, tmp_path):
        world = _with_panel_file(make_world(tmp_path))

        def answer(_doc, _prompt):
            return _answer(
                state="PIPELINE_SUPPLIES_WITH_GAP",
                items=[
                    {
                        "code": "S2",
                        "analysis_quote": "l'accepte dans la semantique preferee",
                    },
                    {
                        "code": "M1",
                        "reading_quote": "ne discute jamais la semantique preferee",
                        "on_central_thesis": True,
                    },
                    {
                        "code": "S1",
                        "analysis_quote": "une phrase qui n'existe dans aucun des deux textes",
                    },
                ],
            )

        judge = FakeJudge(answer)
        assert self._run(world, judge) == 0
        assert len(judge.calls) == len(PANEL), "one call per document, no more"

        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert "PIPELINE_SUPPLIES_WITH_GAP" in table
        assert "`claude-sonnet-5-5`" in table
        assert "`gpt-5.6-luna`" in table
        assert str(SEED) in table
        assert "aveugle à l'ordre, pas au style" in table
        # one invented item per document, and every one of them counted
        assert f"**{len(PANEL)}** item(s) tombés" in table
        assert "quote_not_in_pipeline_text" in table

    def test_the_distribution_counts_every_document(self, tmp_path):
        world = _with_panel_file(make_world(tmp_path))
        judge = FakeJudge(lambda *_: _answer(state="PARITY"))
        self._run(world, judge)
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert f"`PARITY` : **{len(PANEL)}**" in table

    def test_an_unparsed_answer_shows_up_as_unparsed(self, tmp_path):
        world = _with_panel_file(make_world(tmp_path))
        judge = FakeJudge(lambda *_: "je préfère ne pas répondre")
        self._run(world, judge)
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert f"`UNPARSED` : **{len(PANEL)}**" in table

    def test_each_document_record_is_written_with_its_draw(self, tmp_path):
        world = _with_panel_file(make_world(tmp_path))
        self._run(world, FakeJudge())
        for doc in PANEL:
            record = json.loads(
                (world["out"] / f"{doc}.json").read_text(encoding="utf-8")
            )
            assert record["opaque_id"] == doc
            assert record["positions"] == jp.positions(doc, SEED)
            assert record["status_code"] == 200

    def test_costs_are_priced_per_arm(self, tmp_path):
        world = _with_panel_file(make_world(tmp_path))
        self._run(world, FakeJudge())
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert "pipeline : **" in table
        assert "zero-shot : **" in table
        assert "unpriced" not in table.split("## Coût par arm")[1]

    def test_an_unpriced_arm_prints_unpriced_never_zero(self, tmp_path):
        # A known family, an id the price table does not carry: the honest
        # case. An unknown FAMILY stops the run even earlier (#3375), which is
        # its own witness above.
        world = _with_panel_file(
            make_world(tmp_path, zeroshot_model="gpt-9-unpriced-preview")
        )
        self._run(world, FakeJudge())
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert "unpriced" in table

    def test_a_zeroshot_record_without_a_provenance_model_exits_by_name(self, tmp_path):
        world = _with_panel_file(make_world(tmp_path))
        record = json.loads(
            (world["zeroshots"] / f"{PANEL[0]}.json").read_text(encoding="utf-8")
        )
        record["provenance"] = {}
        _write_json(world["zeroshots"] / f"{PANEL[0]}.json", record)
        with pytest.raises(SystemExit) as excinfo:
            asyncio.run(jp.run(_argv(world), judge_call=FakeJudge()))
        assert PANEL[0] in str(excinfo.value)

    def test_nothing_is_written_by_a_dry_run(self, tmp_path):
        world = _with_panel_file(make_world(tmp_path))
        asyncio.run(jp.run(_argv(world, extra=("--dry-run",)), judge_call=FakeJudge()))
        assert not world["out"].exists()

    def test_the_command_line_is_replayable(self, tmp_path):
        """#2353: the recorded command carries the panel selectors — a line
        without them re-runs whatever the directory holds, not the panel."""
        world = _with_panel_file(make_world(tmp_path))
        self._run(world, FakeJudge())
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert "--panel-file" in table
        assert str(world["panel_file"]) in table

    def test_a_failed_call_shows_its_http_code_in_the_row(self, tmp_path):
        """A prompt over the judge's context answers 400: the document is
        UNPARSED and the reader sees WHY — loud, never silent truncation."""

        class Refused:
            async def __call__(self, endpoint, prompt, timeout=600):
                return {"status_code": 400, "error_body_head": "prompt too long"}

        world = _with_panel_file(make_world(tmp_path))
        self._run(world, Refused())
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert "HTTP 400" in table
        assert f"`UNPARSED` : **{len(PANEL)}**" in table

    def test_a_pass_with_failed_calls_exits_non_zero(self, tmp_path):
        """R1141: ten 404s wrote a table and exited 0. A pass that did not
        judge the panel is not a run of the panel, and the exit code says so."""

        class NotFound:
            async def __call__(self, endpoint, prompt, timeout=600):
                return {"status_code": 404, "error_body_head": "not found"}

        world = _with_panel_file(make_world(tmp_path))
        assert self._run(world, NotFound()) == 2
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert f"{len(PANEL)} appel(s) échoué(s), sans réponse du juge" in table
        assert "réponse(s) illisible(s)" not in table

    def test_an_unreadable_answer_is_not_called_a_failed_call(self, tmp_path):
        world = _with_panel_file(make_world(tmp_path))
        assert self._run(world, FakeJudge(lambda *_: "pas de JSON")) == 0
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert f"{len(PANEL)} réponse(s) illisible(s)" in table
        assert "appel(s) échoué(s)" not in table

    def test_the_table_names_the_route_and_the_model_that_answered(self, tmp_path):
        class Answered(FakeJudge):
            async def __call__(self, endpoint, prompt, timeout=600):
                record = await super().__call__(endpoint, prompt, timeout)
                return {**record, "answered_model": "claude-sonnet-5-5-20261001"}

        world = _with_panel_file(make_world(tmp_path))
        self._run(world, Answered())
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert "Route du juge : `test` → hôte `example.invalid`" in table
        assert "`claude-sonnet-5-5-20261001`" in table
        record = json.loads(
            (world["out"] / f"{PANEL[0]}.json").read_text(encoding="utf-8")
        )
        assert record["answered_model"] == "claude-sonnet-5-5-20261001"


class TestAnUnparsedRowCanBeDiagnosed:
    """R1141: 7 of 10 paid answers came back UNPARSED with nothing kept to
    say why — no answer, no stop reason, no refused word."""

    def _run(self, world, judge):
        return asyncio.run(jp.run(_argv(world), judge_call=judge))

    def test_the_answer_and_the_call_facts_are_kept(self, tmp_path):
        class Answering(FakeJudge):
            async def __call__(self, endpoint, prompt, timeout=600):
                record = await super().__call__(endpoint, prompt, timeout)
                return {**record, "stop_reason": "end_turn"}

        world = _with_panel_file(make_world(tmp_path))
        assert self._run(world, Answering()) == 0
        record = json.loads(
            (world["out"] / f"{PANEL[0]}.json").read_text(encoding="utf-8")
        )
        assert record["answer"] == _answer()
        assert record["stop_reason"] == "end_turn"
        assert record["prompt_tokens"] == 2000
        assert record["completion_tokens"] == 400

    def test_a_truncated_answer_is_named_and_the_pass_exits_2(self, tmp_path):
        class CutShort:
            async def __call__(self, endpoint, prompt, timeout=600):
                return {
                    "status_code": 200,
                    "answer": '{"identification": "1", "state": "PIPELINE_SUP',
                    "prompt_tokens": 2000,
                    "completion_tokens": jp.JUDGE_MAX_TOKENS,
                    "usage": {},
                    "stop_reason": "max_tokens",
                }

        world = _with_panel_file(make_world(tmp_path))
        assert self._run(world, CutShort()) == 2
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert "tronquée à la limite de sortie" in table
        assert f"{len(PANEL)} réponse(s) tronquée(s)" in table
        assert "réponse(s) illisible(s)" not in table

    def test_a_state_outside_the_grid_is_kept_by_name(self, tmp_path):
        world = _with_panel_file(make_world(tmp_path))
        judge = FakeJudge(lambda *_: _answer(state="PIPELINE_WINS"))
        assert self._run(world, judge) == 0
        record = json.loads(
            (world["out"] / f"{PANEL[0]}.json").read_text(encoding="utf-8")
        )
        assert record["state"] == "UNPARSED"
        assert record["reported_state"] == "PIPELINE_WINS"
        table = (world["out"] / "TABLE.md").read_text(encoding="utf-8")
        assert "état hors grille : `PIPELINE_WINS`" in table

    def test_the_output_cap_is_not_the_one_that_cut_cycle_0(self):
        assert jp.JUDGE_MAX_TOKENS > 4096


class TestTheAnthropicRoute:
    """R1141: the SDK's ANTHROPIC_BASE_URL has no ``/v1``; the judge posted
    to ``<host>/messages`` and every call of the cycle-0 panel answered 404."""

    def test_the_sdk_form_gets_its_v1_segment(self):
        assert (
            jp.anthropic_messages_url("http://127.0.0.1:3002")
            == "http://127.0.0.1:3002/v1/messages"
        )

    def test_a_base_that_already_ends_in_v1_is_not_doubled(self):
        assert (
            jp.anthropic_messages_url("https://api.anthropic.com/v1/")
            == "https://api.anthropic.com/v1/messages"
        )

    def test_the_default_is_the_vendors_host(self):
        assert (
            jp.anthropic_messages_url(jp.ANTHROPIC_DEFAULT_BASE_URL)
            == "https://api.anthropic.com/v1/messages"
        )

    def test_the_call_posts_to_the_v1_messages_url(self, monkeypatch):
        import httpx

        seen = {}

        class FakeResponse:
            status_code = 200
            text = ""

            def json(self):
                return {
                    "model": "claude-sonnet-5-5",
                    "content": [{"type": "text", "text": "{}"}],
                    "usage": {"input_tokens": 3, "output_tokens": 1},
                }

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

            async def post(self, url, json=None, headers=None):
                seen["url"] = url
                return FakeResponse()

        monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
        endpoint = {
            "api_key": "not-a-key",
            "base_url": "http://127.0.0.1:3002",
            "model_id": "claude-sonnet-5-5",
            "family": "anthropic",
        }
        record = asyncio.run(jp.call_judge(endpoint, "prompt"))
        assert seen["url"] == "http://127.0.0.1:3002/v1/messages"
        assert record["answered_model"] == "claude-sonnet-5-5"
