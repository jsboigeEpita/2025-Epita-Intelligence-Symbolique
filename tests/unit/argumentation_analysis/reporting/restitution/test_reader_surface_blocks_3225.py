"""#3225 — the code's own blocks fail the checks the passes are judged on.

Three leaks, all code-written (the model's prose is not the question):

1. **The reading-bounds block's « (s) » templates are every machinery hit.**
   On R1110 the per-act readability gate fails 8/8 on both acts — and the
   prose without the block scores 0. The 8 hits are the morphology of
   ``reading_record.py``'s templates: « formule(s) … lue(s) » (:262),
   « formule(s) … sur N issues » (:279), « verdict(s) formel(s) » (:280,
   :282), plus the two singleton sites « contre-argument(s) » (:289) and
   « décision(s) » (:292). ``fr_accord.accord`` exists for exactly this
   (#2046) — the count is at hand at every site.
2. **Two headings carry issue numbers.** ``READER_BOUNDS_HEADING``
   (« enregistrement #1737 », printed in Acts II and III, prompt-side block
   at :411 too — the writer copies prompt tokens) and ``COVERAGE_HEADING``
   (« #3159 », Act I since R1109). ``check_reader_vocabulary`` FAILs issue
   numbers, so every pass fails a check the code itself violates.
3. **The verdict-hierarchy label « P1 » leaks unguarded.** R1110 Act III
   opens its second section with « Les P1 d'abord. » — the Act III prompt's
   own instruction copied as if the reader knew the label. ``P1``/``P2``/
   ``P3`` are not a token class of the vocabulary check (base: silent —
   measured on a stored act III carrying « aucun point P1 », same shape).

This witness is born red on the unrepaired module; the population half
enumerates the graft formatters by AST, so the next block anyone grafts is
covered without being listed here.
"""

from __future__ import annotations

import ast
import glob
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution import (
    act1_framing_plugin,
    act2_narrative_plugin,
    act3_conclusion_plugin,
    reading_record,
)
from argumentation_analysis.reporting.restitution.arena_record import (
    build_arena_record,
)
from argumentation_analysis.reporting.restitution.readability_gate import (
    _count_machinery_dumps,
)
from argumentation_analysis.reporting.restitution.reader_vocabulary_check import (
    check_reader_vocabulary,
)
from argumentation_analysis.reporting.restitution.speaker_record import (
    build_speaker_record,
)

# The stored campaign states (gitignored, real corpus) — the measurement
# surface; the witness skips cleanly where they are absent (CI).
_STORED_STATES = sorted(
    glob.glob(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "..",
            "argumentation_analysis",
            "evaluation",
            "results",
            "campaign_2841_lecture",
            "04_annexes",
            "states",
            "state_full_*.json",
        )
    )
)

_PLUGIN_MODULES = (act1_framing_plugin, act2_narrative_plugin, act3_conclusion_plugin)


def _real_shaped_state() -> UnifiedAnalysisState:
    """A state whose reading record exercises every ``(s)`` template site.

    Planted through the real producers (``record_reading_window``, the
    ``add_*`` writers — the #1664 anti-pattern), never by hand-shaping the
    tables. The sites below are the ones the stored corpus states carry;
    R1110's 8 machinery hits all come from these arms.
    """
    state = UnifiedAnalysisState("texte synthétique sans valeur de corpus")
    state.add_counter_argument(
        "thèse synthétique", "réplique synthétique", "distinction", 0.5
    )
    state.add_governance_decision("vote synthétique", "option_a", {"option_a": 0.6})
    # One DECIDED PL record (verdict bool + real formula naming its source) —
    # feeds the units site's « N formule(s) sur M » and « N verdict(s) ».
    state.add_propositional_analysis_result(["p ∧ q"], True, {"p": True, "q": True})
    state.propositional_analysis_results[-1]["formula_sources"] = [["arg_1"]]
    state.add_fol_analysis_result(["∀x (P(x) → Q(x))"], False, ["Q(a)"], 0.5)
    state.fol_analysis_results[-1]["formula_sources"] = [["arg_1"]]
    head = SimpleNamespace(status="selected", offset=0, window=4000)
    # The PL head pass with formulas recorded on the head — the :262 site.
    state.record_reading_window("propositional_logic", head, {"head_formulas": 2})
    # The two units sites — the :279-282 sites.
    state.record_reading_window(
        "propositional_logic_units",
        head,
        {"units": 3, "unit_total": 5, "span_lo": 0, "span_hi": 1200},
    )
    state.record_reading_window(
        "fol_reasoning_units",
        head,
        {"units": 2, "unit_total": 5, "span_lo": 600, "span_hi": 2400},
    )
    # The two singleton sites — :289 and :292.
    state.record_reading_window("counter_argument", head)
    state.record_reading_window("governance", head)
    return state


def _graft_formatters() -> dict[str, object]:
    """Every ``format_*`` function the act plugins graft — by AST, not a list.

    A graft surface is a ``format_*`` name that a plugin both BINDS (an
    import, or a def in the module itself — act1 defines its own coverage
    passage) and CALLS. A new block anyone grafts lands here without being
    declared twice; a bound-but-never-called helper stays out.
    """
    found: dict[str, object] = {}
    for module in _PLUGIN_MODULES:
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8-sig"))
        bound: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                bound.update(
                    (alias.asname or alias.name)
                    for alias in node.names
                    if (alias.asname or alias.name).startswith("format_")
                )
            elif isinstance(node, ast.FunctionDef) and node.name.startswith("format_"):
                bound.add(node.name)
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id.startswith("format_")
        } | {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr.startswith("format_")
        }
        for name in sorted(bound & called):
            fn = getattr(module, name, None)
            if callable(fn):
                found[f"{module.__name__}.{name}"] = fn
    assert found, "the AST enumeration found no graft formatter — vacuous"
    return found


def _render_graft(name: str, fn: object, state: UnifiedAnalysisState) -> str:
    """Invoke one graft formatter with the argument its signature names.

    A ``record`` parameter is resolved by the formatter's OWN module — the
    reading, speaker and arena records all call it ``record``. An unknown
    parameter or record type reddens (the witness learns the new shape);
    nothing is silently skipped."""
    import inspect

    params = list(inspect.signature(fn).parameters)  # type: ignore[arg-type]
    records = {
        reading_record.__name__: reading_record.build_reading_record(state),
        "argumentation_analysis.reporting.restitution.speaker_record": (
            build_speaker_record(state)
        ),
        "argumentation_analysis.reporting.restitution.arena_record": (
            build_arena_record(state)
        ),
    }
    kwargs: dict[str, object] = {}
    for p in params:
        if p == "record":
            module_name = getattr(fn, "__module__", "")
            if module_name not in records:
                pytest.fail(
                    f"graft formatter {name} takes a record from an unknown "
                    f"module {module_name!r} — teach the witness this builder"
                )
            kwargs[p] = records[module_name]
        elif p == "sentence":
            kwargs[p] = "3 unités sur 5 analysées"
        elif p in ("ln", "line"):
            kwargs[p] = reading_record.build_reading_record(state).lines[0]
        elif p == "source_chars":
            kwargs[p] = len(state.raw_text or "")
        else:
            pytest.fail(f"graft formatter {name} takes unknown parameter {p!r}")
    out = fn(**kwargs)  # type: ignore[operator]
    assert isinstance(out, str), f"{name} does not return str"
    return out


class TestBlocksAreClean:
    def test_every_grafted_block_scores_zero_machinery(self) -> None:
        """DoD 1 — the population witness: every grafted block, AST-found."""
        state = _real_shaped_state()
        for name, fn in _graft_formatters().items():
            body = _render_graft(name, fn, state)
            if not body:
                continue  # an absent-case formatter legitimately renders ""
            hits = _count_machinery_dumps(body)
            assert hits == 0, (
                f"{name} carries {hits} machinery signature hit(s) — the "
                "readability gate the passes are judged on (#3225)"
            )

    def test_every_grafted_block_passes_the_vocabulary_check(self) -> None:
        state = _real_shaped_state()
        for name, fn in _graft_formatters().items():
            body = _render_graft(name, fn, state)
            if not body:
                continue
            verdict = check_reader_vocabulary(body)
            assert (
                verdict.band == "PASS"
            ), f"{name} fails the vocabulary check: {verdict.reasons}"


class TestAgreementIsComputed:
    """The anti-pendulum control: the fix agrees the phrase, it does not
    merely delete the parenthetical."""

    def test_singular_and_plural_are_agreed(self) -> None:
        state = _real_shaped_state()
        record = reading_record.build_reading_record(state)
        block = reading_record.format_reading_block(record)
        # The units sites each hold ONE decided record → singular agreement.
        assert "1 verdict formel" in block, block
        assert "1 formule sur 1 issue des unités lues" in block, block
        # The PL head pass recorded TWO head formulas → plural, agreed.
        assert "2 formules de structure globales lues" in block, block
        # The counter/governance sites carry one entry each → singular.
        assert "1 contre-argument" in block, block
        assert "1 décision" in block, block


class TestHierarchyLabelsAreFlagged:
    def test_the_p1_label_is_flagged(self) -> None:
        """DoD 2 — « Les P1 d'abord » (the R1110 Act III leak shape)."""
        body = (
            "Conclusion. Les P1 d'abord, puis les tensions plus faibles. "
            "Le reste du récit suit."
        )
        verdict = check_reader_vocabulary(body)
        assert (
            verdict.band == "FAIL"
        ), "the verdict-hierarchy label reaches the reader unflagged (#3225)"
        assert any("P1" in r for r in verdict.reasons), verdict.reasons

    def test_all_three_tiers_flag(self) -> None:
        for label in ("P1", "P2", "P3"):
            verdict = check_reader_vocabulary(
                f"La hiérarchie ne porte aucun point {label}."
            )
            assert verdict.band == "FAIL", label

    def test_embedded_forms_do_not_flag(self) -> None:
        """« P10 » / « arg_P1 » are not the hierarchy label — boundaries."""
        verdict = check_reader_vocabulary(
            "La grille P10 compte dix niveaux ; arg_P1 tient."
        )
        assert verdict.band == "PASS", verdict.reasons


@pytest.mark.skipif(not _STORED_STATES, reason="no stored campaign states on this seat")
class TestStoredActsAreCovered:
    def test_every_stored_act_carrying_a_hierarchy_label_is_flagged(self) -> None:
        """The measured half of DoD 2 — on the stored acts, base: silent.

        Any stored act body carrying a standalone P1/P2/P3 (measured: one
        stored Act III says « aucun point P1 ») must be flagged by the
        check once the class exists. Corpus text stays in the gitignored
        state files — the witness asserts the verdict, never the prose.
        """
        import json
        import re

        hierarchy_re = re.compile(r"(?<![0-9A-Za-z_])P[123](?![0-9A-Za-z_])")
        checked = 0
        for path in _STORED_STATES:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            for field in ("act1_framing", "act2_narrative", "act3_conclusion"):
                value = data.get(field)
                if not (isinstance(value, str) and hierarchy_re.search(value)):
                    continue
                checked += 1
                verdict = check_reader_vocabulary(value)
                assert verdict.band == "FAIL", (
                    f"{os.path.basename(path)} {field} carries an unflagged "
                    "hierarchy label (#3225)"
                )
        assert checked >= 1, (
            "no stored act carries a hierarchy label — the measured half of "
            "the witness is vacuous on this seat"
        )


class TestMutationsRedden:
    """DoD 3 — re-inserting one ``(s)`` or one ``#NNNN`` reddens the
    population witness (surgical monkeypatch, restored after each)."""

    def test_reinserted_s_template_reddens(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            reading_record,
            "_site_fed",
            lambda site, state: "1 formule(s) lue(s)",
        )
        state = _real_shaped_state()
        record = reading_record.build_reading_record(state)
        block = reading_record.format_reading_block(record)
        assert _count_machinery_dumps(block) >= 1

    def test_reinserted_issue_number_reddens(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            reading_record,
            "READER_BOUNDS_HEADING",
            "Bornes de lecture du run (enregistrement #1737)",
        )
        state = _real_shaped_state()
        record = reading_record.build_reading_record(state)
        passage = reading_record.format_reader_bounds_passage(record)
        verdict = check_reader_vocabulary(passage)
        assert verdict.band == "FAIL", verdict.reasons

    def test_coverage_heading_number_reddens(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            act1_framing_plugin,
            "COVERAGE_HEADING",
            "Couverture de l'analyse (chiffres du pipeline, #3159)",
        )
        verdict = check_reader_vocabulary(
            act1_framing_plugin.format_coverage_passage("3 unités sur 5")
        )
        assert verdict.band == "FAIL", verdict.reasons
