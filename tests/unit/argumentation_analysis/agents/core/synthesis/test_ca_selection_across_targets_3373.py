"""#3373 — the counter-argument briefing selects ACROSS targets, and says each
target's population.

The briefing built ``for ca in counter_arguments[:15]``: the first fifteen in
INSERTION order. The producer writes its output target by target, so the prefix
holds the first four targets and nothing beyond them. On the R1137a pass the
record carried 43 counters over 10 countered units; the writer saw 15 counters
over 4 units, and it counted its briefing: it wrote « Cinq contre-arguments »
for arg_29, which carries six.

The repair is two halves at one seam:
- the selection walks the TARGETS, not the list — every countered unit gets one
  counter before any unit gets a second, while the units fit the cap; within a
  target the producer's order holds;
- a line whose target is cut states that target's population (``(1 of 6 on this
  target)``), so a count the writer gives comes from the record, not from the
  cut.

Anti-pendulum, pinned below: the cap stays 15 (#2967/#3155 line untouched), and
a population that fits the cap renders byte for byte as on main — the count
appears only where a target is actually cut.

Every fixture is synthetic: opaque ids and invented filler text.
Deterministic — no JVM, no LLM, no network.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)

#: The R1137a shape, synthesised: 43 counters over 10 countered units, written
#: target by target — exactly how the counter-argument phase emits them.
_COUNTS = [6, 5, 5, 5, 4, 4, 4, 4, 3, 3]  # sums to 43
_TARGETS = [f"arg_{i}" for i in range(1, len(_COUNTS) + 1)]
_CAP = 15


def _population() -> list:
    counters = []
    index = 0
    for target, count in zip(_TARGETS, _COUNTS):
        for _ in range(count):
            index += 1
            counters.append(
                {
                    "id": f"ca_{index}",
                    "strategy": "",
                    "score": 0.5,
                    "counter_content": f"invented filler {index}",
                    "target_arg_id": target,
                }
            )
    return counters


def _state(**fields) -> SimpleNamespace:
    base = dict(
        identified_arguments={},
        identified_fallacies={},
        counter_arguments=[],
        argument_quality_scores={},
        propositional_analysis_results=[],
        fol_analysis_results=[],
        modal_analysis_results=[],
        dung_frameworks={},
        jtms_retraction_chain=[],
        belief_revision_results=[],
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _briefing(state) -> str:
    return DeepSynthesisAgent.build_artifact_briefing(state)


def _counter_lines(briefing: str) -> list:
    return [
        line
        for line in briefing.splitlines()
        if line.startswith("[artifact:counter_arguments.")
    ]


def _briefed(state) -> list:
    return _counter_lines(_briefing(state))


def _target_of(line: str) -> str:
    """The target an artifact line names (``target=arg_1`` or with a count)."""
    for token in line.split():
        if token.startswith("target="):
            return token[len("target=") :]
    raise AssertionError(f"no target on {line!r}")


# ============================================================================
# The measured defect — six of ten countered units reach no writer
# ============================================================================


class TestEveryCounteredTargetReachesTheBriefing:
    def test_each_of_the_ten_targets_is_briefed(self):
        """Red on main: the prefix holds arg_1..arg_4 and stops."""
        briefed = {
            _target_of(line)
            for line in _briefed(_state(counter_arguments=_population()))
        }

        assert briefed == set(_TARGETS)

    def test_the_cap_is_not_raised(self):
        """Anti-pendulum: the same 15 slots, shared across targets (#2967)."""
        assert len(_briefed(_state(counter_arguments=_population()))) == _CAP

    def test_no_target_takes_a_second_before_all_have_one(self):
        """15 = 10 firsts + 5 seconds: five targets carry two, five carry one."""
        counts = {}
        for line in _briefed(_state(counter_arguments=_population())):
            target = _target_of(line)
            counts[target] = counts.get(target, 0) + 1

        assert sorted(counts.values(), reverse=True) == [2, 2, 2, 2, 2, 1, 1, 1, 1, 1]

    def test_within_a_target_the_producers_order_holds(self):
        lines = _briefed(_state(counter_arguments=_population()))
        arg_1 = [
            ln
            for ln in lines
            if _target_of(ln).startswith("arg_1 ") or _target_of(ln) == "arg_1"
        ]

        assert len(arg_1) == 2
        assert "ca_1]" in arg_1[0] and "ca_2]" in arg_1[1]


# ============================================================================
# The other half — a cut target states its population
# ============================================================================


class TestACutTargetStatesItsPopulation:
    def test_the_line_states_the_targets_population(self):
        """arg_29 in R1137a carries 6; the writer must read 6, not the cut."""
        lines = _briefed(_state(counter_arguments=_population()))
        arg_1 = [
            ln for ln in lines if ln.startswith("[artifact:counter_arguments.ca_1]")
        ][0]

        assert "target=arg_1 (1 of 6 on this target)" in arg_1

    def test_the_count_is_the_records_not_the_cuts(self):
        """arg_2 carries 5 and is briefed once — the line still says 5."""
        lines = _briefed(_state(counter_arguments=_population()))
        arg_2 = [
            ln for ln in lines if ln.startswith("[artifact:counter_arguments.ca_7]")
        ][0]

        assert "target=arg_2 (1 of 5 on this target)" in arg_2

    def test_an_unresolved_counter_fabricates_no_count(self):
        """No target, no population: the #3201 wording stands untouched."""
        counters = [
            {
                "id": "ca_y",
                "strategy": "",
                "score": 0.31,
                "counter_content": "invented filler beta",
                "target_unresolved_reason": "target id absent from the run",
            }
        ]
        line = _briefed(_state(counter_arguments=counters))[0]

        assert "target=unresolved (target id absent from the run)" in line
        assert "on this target" not in line


# ============================================================================
# Control — a population that fits the cap is briefed exactly as on main
# ============================================================================


class TestAPopulationThatFitsIsUntouched:
    def _ten(self) -> list:
        return [
            {
                "id": f"ca_{i}",
                "strategy": "",
                "score": 0.5,
                "counter_content": f"invented filler {i}",
                "target_arg_id": f"arg_{i}",
            }
            for i in range(1, 11)
        ]

    def test_no_count_is_printed_when_nothing_is_cut(self):
        lines = _briefed(_state(counter_arguments=self._ten()))

        assert len(lines) == 10
        assert all("on this target" not in ln for ln in lines)

    def test_the_line_is_the_old_line_byte_for_byte(self):
        line = _briefed(_state(counter_arguments=self._ten()))[0]

        assert line == (
            "[artifact:counter_arguments.ca_1] score=0.5 target=arg_1 "
            "— invented filler 1"
        )

    def test_one_counter_fewer_than_the_cap_is_still_untouched(self):
        """14 counters over 14 targets: nothing is cut, nothing is said."""
        counters = self._ten()[:9] + [
            {
                "id": "ca_10",
                "strategy": "",
                "score": 0.5,
                "counter_content": "invented filler 10",
                "target_arg_id": "arg_10",
            }
        ]
        lines = _briefed(_state(counter_arguments=counters))

        assert len(lines) == 10
        assert all("on this target" not in ln for ln in lines)


# ============================================================================
# R1139 rework — ``cut`` is decided on what is SHOWN, never on the rank
# ============================================================================


def _multi_per_target() -> list:
    """12 counters over 5 targets, written target by target, cap 15.

    The ordinary shape of the phase — several counters per unit — and the one
    the first witness missed: it gave one counter per target, where "rank <
    population" and "shown < population" agree by accident.
    """
    counts = [3, 3, 2, 2, 2]  # sums to 12, all of them under the cap of 15
    counters = []
    index = 0
    for target_index, count in enumerate(counts, start=1):
        for _ in range(count):
            index += 1
            counters.append(
                {
                    "id": f"ca_{index}",
                    "strategy": "",
                    "score": 0.5,
                    "counter_content": f"invented filler {index}",
                    "target_arg_id": f"arg_{target_index}",
                }
            )
    return counters


class TestCutIsDecidedOnWhatIsShown:
    def test_a_population_that_fits_marks_no_target_as_cut(self):
        """Red on the R1293 head: ``cut=rank < population`` flagged every line
        of a target but its last, so 12 counters over 5 targets under a cap of
        15 printed a cut that never happened."""
        lines = _briefed(_state(counter_arguments=_multi_per_target()))

        assert len(lines) == 12
        assert [ln for ln in lines if "on this target" in ln] == []

    def test_every_line_of_a_fitting_population_is_the_old_line(self):
        """The same fact, read on the rendered text: byte for byte, main's line.

        The briefing follows the SELECTION order (round-robin), so the ids do
        not come out in sequence — each line is looked up by its id.
        """
        lines = _briefed(_state(counter_arguments=_multi_per_target()))
        by_id = {
            ln.split("]")[0][len("[artifact:counter_arguments.") :]: ln for ln in lines
        }

        assert by_id["ca_1"] == (
            "[artifact:counter_arguments.ca_1] score=0.5 target=arg_1 "
            "— invented filler 1"
        )
        assert by_id["ca_12"] == (
            "[artifact:counter_arguments.ca_12] score=0.5 target=arg_5 "
            "— invented filler 12"
        )


class TestACutTargetStatesTheCountOnEachShownLine:
    def test_a_target_shown_twice_of_six_names_the_six(self):
        """CONTROL — green before and after the rework: where a cut is real,
        every shown line of that target carries the record's count."""
        counters = [
            {
                "id": f"ca_{i}",
                "strategy": "",
                "score": 0.5,
                "counter_content": f"invented filler {i}",
                "target_arg_id": "arg_1",
            }
            for i in range(1, 7)  # six counters on one target
        ] + [
            {
                "id": f"cb_{i}",
                "strategy": "",
                "score": 0.5,
                "counter_content": f"invented filler b{i}",
                "target_arg_id": f"arg_x{i}",
            }
            for i in range(1, 14)  # thirteen single-counter targets: 14 firsts
        ]
        lines = _briefed(_state(counter_arguments=counters))
        arg_1 = [ln for ln in lines if _target_of(ln) == "arg_1"]

        assert len(arg_1) == 2, (
            "the fixture must show exactly two of arg_1's six counters — "
            f"got {len(arg_1)}"
        )
        assert "arg_1 (1 of 6 on this target)" in arg_1[0]
        assert "arg_1 (2 of 6 on this target)" in arg_1[1]
