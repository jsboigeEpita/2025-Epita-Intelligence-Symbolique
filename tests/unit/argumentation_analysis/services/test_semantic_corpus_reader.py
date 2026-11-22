"""#3548 — the corpus is a second reader: the same claim, elsewhere.

Measured before this change: on the recorded cycle-6 panel states,
``semantic_index_refs`` was non-empty on **0 of 10** documents — the refs
branch had no producer (``_write_semantic_index_to_state``'s ``results``
arm answered a list no phase ever emitted, storing ``ctx["input_data"]``
as ``query`` plus a ``snippet`` — the two text fields the sanitizer has to
strip). The repoint decision (#3387, decision 1) left the panel-wide index
to "a second reader"; this is it.

The chain, per the issue's asks:

- **KB (shape A)** — ``build_corpus_kb`` chunks every OTHER corpus document
  (``load_extract_definitions``'s in-memory output, opaque ids) and embeds
  the chunks; an entry is ``{opaque doc id, start, end, vector}``, dropped
  with the process. Nothing is persisted (#3387 shape A; shape B stays
  deferred).
- **Query (ask 2)** — ``corpus_claim_from_state`` takes the claim the
  strategist's ``players`` attribute to a side, else the first reading's
  thesis. The historian's ``context_note`` is NEVER a source.
- **Solver (ask 5)** — cosine, the same ``_cosine`` v1 uses.
- **Answer (ask 4)** — the other documents' chunks above a STATED
  threshold, as ``{doc, start, end, score}``; the analysed document is
  excluded from the KB by id.
- **State (ask 7)** — the refs branch is replaced by this offsets-only
  record: ``add_semantic_index_ref`` takes no ``query`` and no
  ``snippet``; the reader is Act I's framing (ask 6), which renders
  « la même thèse figure déjà dans un autre document du corpus » with the
  opaque id and the measured position.

The threshold is measured, not guessed: on this planted corpus (crc32
bag-of-words fake, the ``test_semantic_repoint_3387`` pattern), the
paraphrase chunk of doc_Q scores **0.5951** against the claim, the
mutation that removes it leaves **0.4281** at best, and doc_R (school
meals) never exceeds **0.2593** — ``CORPUS_MATCH_THRESHOLD = 0.5`` accepts
the finding, rejects the mutated corpus AND the off-topic document.

Witnesses (all free: no key, no network, no real corpus — planted text,
loopback fake):

- the claim of doc_P returns doc_Q's paraphrase span and no doc_R span;
- the analysed document never answers its own query (excluded by id);
- the recorded state entry holds no string field other than the opaque
  ids — no ``query``, no ``snippet`` (#3548 ask 7, assertion 2);
- the persona: a strategist player's ``interests`` is the claim, the
  thesis is the fallback, the historian's note never qualifies;
- the act reader renders the finding sentence and stays silent when the
  record is empty (honest absence);
- mutation: doc_Q's paraphrase removed from the planted corpus ⇒ no match
  above the threshold — the witness reddens (it does not depend on
  nothing);
- positive control (green on ``main`` too): the same fake drives v1's
  ``retrieve_priority_spans`` over doc_Q alone and places a span on the
  paraphrase — the witness sees the solver it extends.
"""

from __future__ import annotations

import re
import zlib
from typing import Any, Dict, List, Sequence, Tuple

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.services import semantic_retrieval as sr

# ---------------------------------------------------------------------------
# A deterministic, network-free embedder — the repoint witness's pattern.
# ---------------------------------------------------------------------------

_DIM = 96


def _vector(text: str) -> List[float]:
    vec = [0.0] * _DIM
    for word in re.findall(r"[0-9a-zà-ÿ]+", text.lower()):
        vec[zlib.crc32(word.encode("utf-8")) % _DIM] += 1.0
    return vec


def _fake_post_embeddings(route: Any, texts: Sequence[str]) -> List[List[float]]:
    return [_vector(t) for t in texts]


@pytest.fixture(autouse=True)
def _fake_endpoint(monkeypatch):
    """Every witness runs the real code path against a fake embedder."""
    monkeypatch.setattr(sr, "_post_embeddings", _fake_post_embeddings)


# ---------------------------------------------------------------------------
# The planted corpus (ask 1): invented content, opaque ids, nothing real.
# ---------------------------------------------------------------------------

#: The claim the persona looks up — in doc_P's own words.
CLAIM = (
    "les transports en commun gratuits se financeraient eux-mêmes par la baisse "
    "de l'entretien des routes"
)

#: doc_P asserts the claim (it plays the ANALYSED document).
DOC_P_TEXT = (
    "Notre groupe l'affirme sans détour : des transports en commun gratuits dans "
    "toute l'agglomération se financeraient eux-mêmes. La baisse de la circulation "
    "réduirait l'entretien des routes, et cette économie compenserait la "
    "disparition des billets dès la première année."
)

#: doc_Q makes the same claim in other words, inside a longer paragraph.
DOC_Q_TEXT = (
    "Le conseil municipal a adopté trois motions hier soir, dont une sur la voirie. "
    "Une élue de la majorité a défendu des transports en commun gratuits : selon son "
    "calcul, la baisse du trafic paierait l'entretien des routes, moins usées, et la "
    "disparition du ticket suivrait. L'opposition a demandé une étude chiffrée avant "
    "tout arbitrage budgétaire, le maire ayant promis un débat en séance publique."
)

#: The paraphrase sentence, on its own, for the mutation control.
_DOC_Q_PARAPHRASE = (
    "Une élue de la majorité a défendu des transports en commun gratuits : selon son "
    "calcul, la baisse du trafic paierait l'entretien des routes, moins usées, et la "
    "disparition du ticket suivrait."
)

#: doc_Q without its paraphrase — the mutation the DoD names.
DOC_Q_MUTATED_TEXT = (
    "Le conseil municipal a adopté trois motions hier soir, dont une sur la voirie. "
    "L'opposition a demandé une étude chiffrée avant tout arbitrage budgétaire, "
    "le maire ayant promis un débat en séance publique."
)

#: doc_R is about school meals — the off-topic control.
DOC_R_TEXT = (
    "La cantine scolaire sert chaque midi deux mille repas dans douze établissements. "
    "Le menu de la semaine a été établi avec une diététicienne : légumes de saison, "
    "produits locaux et viande une fois par jour. Les parents d'élèves réclament "
    "davantage de choix végétariens et une traçabilité des fournisseurs."
)


def _definitions(with_paraphrase: bool = True) -> List[Dict[str, Any]]:
    """The planted corpus in ``load_extract_definitions``' item shape."""
    doc_q = DOC_Q_TEXT if with_paraphrase else DOC_Q_MUTATED_TEXT
    return [
        {"id": "doc_p", "source_name": "planted_p", "full_text": DOC_P_TEXT},
        {"id": "doc_q", "source_name": "planted_q", "full_text": doc_q},
        {"id": "doc_r", "source_name": "planted_r", "full_text": DOC_R_TEXT},
    ]


def _route() -> sr.EmbeddingRoute:
    return sr.EmbeddingRoute("k", "http://test/v1", "fake-embed", "declared")


def _kb(exclude: str = "doc_p", with_paraphrase: bool = True):
    return sr.build_corpus_kb(_definitions(with_paraphrase), _route(), exclude)


# ---------------------------------------------------------------------------
# The corpus reader (asks 3, 4, 5) — born red on main: none of it exists.
# ---------------------------------------------------------------------------


class TestTheCorpusIsASecondReader:
    def test_the_claim_returns_doc_q_and_not_doc_r(self) -> None:
        kb, reason = _kb()
        assert reason == ""
        out = sr.query_corpus_for_claim(CLAIM, kb, _route())
        matches = out["matches"]
        assert matches, (
            f"no corpus match above the threshold — the reader found nothing "
            f"for the claim ({out!r})"
        )
        assert matches[0]["doc"] == "doc_q", (
            f"the best match is {matches[0]['doc']!r}, expected doc_q — the "
            f"paraphrase did not outrank the rest"
        )
        # The matched span points at the paraphrase, not at filler.
        span = matches[0]
        assert (
            "transports en commun gratuits" in DOC_Q_TEXT[span["start"] : span["end"]]
        ), (
            f"the span ({span['start']}, {span['end']}) does not cover the "
            f"paraphrase passage"
        )
        assert all(
            m["doc"] != "doc_r" for m in matches
        ), f"doc_r (school meals) matched the transport claim: {matches!r}"

    def test_the_analysed_document_never_answers_its_own_query(self) -> None:
        kb, _ = _kb(exclude="doc_p")
        assert all(
            e.doc_id != "doc_p" for e in kb
        ), "the analysed document is in its own KB — the exclusion by id failed"

    def test_the_answer_is_offsets_and_a_stated_threshold(self) -> None:
        kb, _ = _kb()
        out = sr.query_corpus_for_claim(CLAIM, kb, _route())
        assert (
            out["threshold"] == sr.CORPUS_MATCH_THRESHOLD
        ), "the threshold must ride in the answer — a run reports the bar it applied"
        for m in out["matches"]:
            assert set(m) == {
                "doc",
                "start",
                "end",
                "score",
            }, f"a match entry carries more than the offsets shape: {m!r}"
            assert isinstance(m["start"], int) and isinstance(m["end"], int)
            assert m["end"] > m["start"] >= 0
            assert m["score"] >= out["threshold"]

    def test_a_corpus_without_chunkable_text_names_itself(self) -> None:
        empty = [{"id": "doc_x", "source_name": "x", "full_text": "  "}]
        kb, reason = sr.build_corpus_kb(empty, _route(), "doc_p")
        assert kb == []
        assert reason, "an empty KB must name why, not pass silently"


class TestMutationControl:
    def test_without_doc_q_paraphrase_the_finding_disappears(self) -> None:
        """DoD mutation: doc_Q's paraphrase removed ⇒ no match above the bar.

        Measured: the mutated corpus's best chunk scores 0.4281 against the
        claim (function-word overlap) — under the 0.5 bar, the finding is
        gone and this test proves the witness depends on the paraphrase.
        """
        kb, _ = _kb(with_paraphrase=False)
        out = sr.query_corpus_for_claim(CLAIM, kb, _route())
        assert not any(m["doc"] == "doc_q" for m in out["matches"]), (
            f"doc_q still matched without its paraphrase: {out['matches']!r} — "
            f"the threshold does not separate the claim from function words"
        )


# ---------------------------------------------------------------------------
# The persona (ask 2) — the strategist's claim, the thesis fallback, never
# the historian.
# ---------------------------------------------------------------------------


class TestTheClaimComesFromThePersona:
    def _state(self, **fields: Any) -> UnifiedAnalysisState:
        state = UnifiedAnalysisState(initial_text=DOC_P_TEXT)
        for name, value in fields.items():
            setattr(state, name, value)
        return state

    def test_a_strategist_player_claim_is_the_query(self) -> None:
        state = self._state(
            strategic_read={
                "players": [
                    {
                        "name": "la majorité",
                        "role": "coalition",
                        "stance": "for",
                        "interests": CLAIM,
                    }
                ],
                "options": [],
                "preferences": {},
                "reading": "",
                "game": {},
                "status": "ok",
            }
        )
        claim, reason = sr.corpus_claim_from_state(state)
        assert (claim, reason) == (CLAIM, "")

    def test_the_first_reading_thesis_is_the_fallback(self) -> None:
        state = self._state()
        state.defining_moves = {
            "moves": [
                {"kind": "thesis", "quote": CLAIM, "reading": "un calcul", "offset": 0}
            ],
            "dropped_quotes": 0,
            "status": "ok",
            "read_scope": {},
            "basis": "first_reading",
        }
        claim, reason = sr.corpus_claim_from_state(state)
        assert (
            claim and CLAIM[:30] in claim
        ), f"the thesis fallback did not fire: {claim!r} ({reason!r})"

    def test_the_historian_note_is_never_a_source(self) -> None:
        state = self._state(
            historical_context={
                "situation": CLAIM,  # the historian holds the same words…
                "items": [],
                "status": "ok",
            },
            strategic_read={"players": [], "status": "no_llm"},
        )
        state.defining_moves = {"moves": [], "status": "no_llm"}
        claim, reason = sr.corpus_claim_from_state(state)
        assert claim == "", (
            "the historian's context leaked into the corpus query — ask 2 "
            f"forbids it ({claim!r})"
        )
        assert reason

    def test_a_state_with_nothing_to_say_says_it(self) -> None:
        claim, reason = sr.corpus_claim_from_state(None)
        assert claim == "" and reason


# ---------------------------------------------------------------------------
# The state record (ask 7) — offsets only, no query, no snippet.
# ---------------------------------------------------------------------------


class TestTheRecordIsOffsetsOnly:
    def _written(self, matches: List[Dict[str, Any]]) -> UnifiedAnalysisState:
        from argumentation_analysis.orchestration.state_writers import (
            _write_semantic_index_to_state,
        )

        state = UnifiedAnalysisState(initial_text=DOC_P_TEXT)
        _write_semantic_index_to_state({"corpus_matches": matches}, state, {})
        return state

    def test_the_entry_holds_no_string_field_other_than_the_opaque_id(
        self,
    ) -> None:
        state = self._written(
            [{"doc": "doc_q", "start": 79, "end": 270, "score": 0.5951}]
        )
        refs = state.semantic_index_refs
        assert len(refs) == 1
        entry = refs[0]
        assert (
            "query" not in entry and "snippet" not in entry
        ), f"the refs record still carries text fields: {entry!r}"
        for value in entry.values():
            if isinstance(value, str):
                assert value in ("doc_q",) or value.startswith("si_"), (
                    f"a string other than the opaque ids entered the record: "
                    f"{value!r} in {entry!r}"
                )
        assert (entry["document_id"], entry["start"], entry["end"]) == (
            "doc_q",
            79,
            270,
        )

    def test_bad_entries_are_dropped_not_repaired(self) -> None:
        state = self._written(
            [
                {"doc": "doc_q", "start": 79, "end": 270, "score": 0.6},
                {"doc": "doc_q", "start": 300, "end": 200, "score": 0.9},  # end < start
                {"doc": "", "start": 0, "end": 10, "score": 0.9},  # no id
                "not a dict",
            ]
        )
        assert len(state.semantic_index_refs) == 1

    def test_the_legacy_results_arm_is_gone(self) -> None:
        """The producer-less arm stored ``ctx["input_data"]`` as ``query`` —
        the exact text field this issue retires. Feeding it must record
        nothing."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_semantic_index_to_state,
        )

        state = UnifiedAnalysisState(initial_text=DOC_P_TEXT)
        _write_semantic_index_to_state(
            {"results": [{"id": "doc_q", "score": 0.9, "snippet": "texte"}]},
            state,
            {"input_data": "la requête"},
        )
        assert state.semantic_index_refs == []

    def test_an_output_without_corpus_matches_records_nothing(self) -> None:
        state = self._written([])
        assert state.semantic_index_refs == []


# ---------------------------------------------------------------------------
# The act reader (ask 6) — Act I's framing names the other document.
# ---------------------------------------------------------------------------


class TestActIReadsTheCorpusEcho:
    def _state_with_refs(self) -> UnifiedAnalysisState:
        state = UnifiedAnalysisState(initial_text=DOC_P_TEXT)
        state.add_semantic_index_ref(
            document_id="doc_q", start=79, end=270, score=0.5951
        )
        return state

    def test_the_evidence_carries_the_record(self) -> None:
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            build_act1_evidence,
        )

        evidence = build_act1_evidence(self._state_with_refs())
        assert (
            evidence.semantic_index_refs
        ), "Act I's evidence does not carry the corpus record — no reader"

    def test_the_block_names_the_other_document(self) -> None:
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            _format_corpus_echo_block,
        )

        block = _format_corpus_echo_block(
            [
                {
                    "id": "si_1",
                    "document_id": "doc_q",
                    "start": 79,
                    "end": 270,
                    "score": 0.5951,
                }
            ]
        )
        assert "doc_q" in block, "the finding does not name the other document"
        assert (
            "un autre document du corpus" in block
        ), f"the finding sentence is missing: {block!r}"
        assert (
            "79" in block and "270" in block
        ), "the measured position does not ride with the finding"
        assert block.strip(), "an empty block for a present finding"

    def test_an_empty_record_renders_no_block(self) -> None:
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            _format_corpus_echo_block,
        )

        assert _format_corpus_echo_block([]) == ""


# ---------------------------------------------------------------------------
# Positive control — the solver this reader extends, green on main too.
# ---------------------------------------------------------------------------


class TestPositiveControlV1Solver:
    def test_the_same_fake_drives_v1_over_doc_q_alone(self) -> None:
        """``retrieve_priority_spans`` (v1) over doc_Q's own text places a
        span on the paraphrase — the corpus solver reuses this cosine, and
        this control stays green on ``main`` (it exists there)."""
        out = sr.retrieve_priority_spans(DOC_Q_TEXT, CLAIM, _route())
        spans = out["spans"]
        assert spans, "v1 ranked nothing — the fake or the solver is broken"
        assert any(
            "transports en commun gratuits" in DOC_Q_TEXT[start:end]
            for start, end in spans
        ), f"no span covers the paraphrase passage: {spans!r}"
