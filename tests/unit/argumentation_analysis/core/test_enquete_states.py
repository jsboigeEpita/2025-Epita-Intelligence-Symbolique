# tests/unit/argumentation_analysis/core/test_enquete_states.py
"""Tests for BaseWorkflowState, EnquetePoliciereState, EnqueteCluedoState."""

import pytest

from argumentation_analysis.core.enquete_states import (
    BaseWorkflowState,
    EnquetePoliciereState,
    EnqueteCluedoState,
)

# ── BaseWorkflowState ──


class TestBaseWorkflowState:
    @pytest.fixture
    def state(self):
        return BaseWorkflowState({"key": "value"})

    def test_init(self, state):
        assert state.initial_context == {"key": "value"}
        assert state.workflow_id is not None
        assert state.tasks == []
        assert state.results == []
        assert state.log_messages == []
        assert state.final_output == {}
        assert state._next_agent_designated is None

    def test_init_with_id(self):
        s = BaseWorkflowState({}, workflow_id="custom-id")
        assert s.workflow_id == "custom-id"

    # -- Tasks --
    def test_add_task(self, state):
        task = state.add_task("Analyze data", "agent_1")
        assert task["description"] == "Analyze data"
        assert task["assignee"] == "agent_1"
        assert task["status"] == "pending"
        assert len(state.tasks) == 1

    def test_add_task_custom_id(self, state):
        task = state.add_task("desc", "agent", task_id="t-1")
        assert task["task_id"] == "t-1"

    def test_get_task(self, state):
        task = state.add_task("desc", "agent", task_id="t-1")
        assert state.get_task("t-1") is task

    def test_get_task_nonexistent(self, state):
        assert state.get_task("nope") is None

    def test_update_task_status(self, state):
        state.add_task("desc", "agent", task_id="t-1")
        assert state.update_task_status("t-1", "completed") is True
        assert state.get_task("t-1")["status"] == "completed"

    def test_update_task_status_nonexistent(self, state):
        assert state.update_task_status("nope", "done") is False

    def test_get_tasks_all(self, state):
        state.add_task("t1", "a1")
        state.add_task("t2", "a2")
        assert len(state.get_tasks()) == 2

    def test_get_tasks_by_assignee(self, state):
        state.add_task("t1", "a1")
        state.add_task("t2", "a2")
        assert len(state.get_tasks(assignee="a1")) == 1

    def test_get_tasks_by_status(self, state):
        state.add_task("t1", "a1", task_id="t-1")
        state.add_task("t2", "a2", task_id="t-2")
        state.update_task_status("t-1", "done")
        assert len(state.get_tasks(status="done")) == 1

    # -- Results --
    def test_add_result(self, state):
        result = state.add_result("q1", "agent_1", {"data": 42})
        assert result["query_id"] == "q1"
        assert result["agent_source"] == "agent_1"
        assert result["content"]["data"] == 42
        assert len(state.results) == 1

    def test_get_results_all(self, state):
        state.add_result("q1", "a1", {})
        state.add_result("q2", "a2", {})
        assert len(state.get_results()) == 2

    def test_get_results_by_query(self, state):
        state.add_result("q1", "a1", {})
        state.add_result("q2", "a1", {})
        assert len(state.get_results(query_id="q1")) == 1

    def test_get_results_by_agent(self, state):
        state.add_result("q1", "a1", {})
        state.add_result("q1", "a2", {})
        assert len(state.get_results(agent_source="a2")) == 1

    # -- Logs --
    def test_add_log_message(self, state):
        state.add_log_message("agent_1", "info", "hello")
        assert len(state.log_messages) == 1
        assert state.log_messages[0]["agent_source"] == "agent_1"
        assert state.log_messages[0]["message_type"] == "info"

    # -- Final output --
    def test_set_get_final_output(self, state):
        state.set_final_output({"conclusion": "done"})
        assert state.get_final_output() == {"conclusion": "done"}

    # -- Next agent --
    def test_designate_next_agent(self, state):
        state.designate_next_agent("sherlock")
        assert state.get_designated_next_agent() == "sherlock"

    def test_no_designated_agent(self, state):
        assert state.get_designated_next_agent() is None


# ── EnquetePoliciereState ──


class TestEnquetePoliciereState:
    @pytest.fixture
    def state(self):
        return EnquetePoliciereState("Murder at the library", {"scene": "library"})

    def test_init(self, state):
        assert state.description_cas == "Murder at the library"
        assert state.elements_identifies == []
        assert state.belief_sets == {}
        assert state.query_log == []
        assert state.hypotheses_enquete == []

    def test_get_case_description(self, state):
        assert state.get_case_description() == "Murder at the library"

    def test_update_case_description(self, state):
        state.update_case_description("Updated description")
        assert state.get_case_description() == "Updated description"

    # -- Elements --
    def test_add_identified_element(self, state):
        elem = state.add_identified_element("witness", "Saw suspect", "report")
        assert elem["type"] == "witness"
        assert elem["description"] == "Saw suspect"
        assert elem["source"] == "report"
        assert len(state.elements_identifies) == 1

    def test_get_identified_elements_all(self, state):
        state.add_identified_element("witness", "W1", "s1")
        state.add_identified_element("evidence", "E1", "s2")
        assert len(state.get_identified_elements()) == 2

    def test_get_identified_elements_by_type(self, state):
        state.add_identified_element("witness", "W1", "s1")
        state.add_identified_element("evidence", "E1", "s2")
        assert len(state.get_identified_elements("witness")) == 1

    # -- Belief sets --
    def test_add_and_get_belief_set(self, state):
        state.add_or_update_belief_set("bs1", "p(a).")
        assert state.get_belief_set_content("bs1") == "p(a)."

    def test_update_belief_set(self, state):
        state.add_or_update_belief_set("bs1", "v1")
        state.add_or_update_belief_set("bs1", "v2")
        assert state.get_belief_set_content("bs1") == "v2"

    def test_get_belief_set_nonexistent(self, state):
        assert state.get_belief_set_content("nope") is None

    def test_remove_belief_set(self, state):
        state.add_or_update_belief_set("bs1", "content")
        assert state.remove_belief_set("bs1") is True
        assert state.get_belief_set_content("bs1") is None

    def test_remove_belief_set_nonexistent(self, state):
        assert state.remove_belief_set("nope") is False

    def test_list_belief_sets(self, state):
        state.add_or_update_belief_set("bs1", "c1")
        state.add_or_update_belief_set("bs2", "c2")
        assert set(state.list_belief_sets()) == {"bs1", "bs2"}

    # -- Query log --
    def test_add_query_log_entry(self, state):
        qid = state.add_query_log_entry("watson", "Is X true?", "bs1")
        assert isinstance(qid, str)
        assert len(state.query_log) == 1
        assert state.query_log[0]["status_processing"] == "pending"

    def test_update_query_log_status(self, state):
        qid = state.add_query_log_entry("watson", "query", "bs1")
        assert state.update_query_log_status(qid, "completed") is True

    def test_update_query_log_nonexistent(self, state):
        assert state.update_query_log_status("nope", "done") is False

    def test_get_query_log_entries_all(self, state):
        state.add_query_log_entry("watson", "q1", "bs1")
        state.add_query_log_entry("sherlock", "q2", "bs1")
        assert len(state.get_query_log_entries()) == 2

    def test_get_query_log_by_agent(self, state):
        state.add_query_log_entry("watson", "q1", "bs1")
        state.add_query_log_entry("sherlock", "q2", "bs1")
        assert len(state.get_query_log_entries(queried_by="watson")) == 1

    def test_get_query_log_by_bs(self, state):
        state.add_query_log_entry("watson", "q1", "bs1")
        state.add_query_log_entry("watson", "q2", "bs2")
        assert len(state.get_query_log_entries(belief_set_id_cible="bs2")) == 1

    # -- Hypotheses --
    def test_add_hypothesis(self, state):
        h = state.add_hypothesis("Butler did it", 0.8)
        assert h["text"] == "Butler did it"
        assert h["confidence_score"] == 0.8
        assert h["status"] == "new"
        assert h["supporting_evidence_ids"] == []

    def test_get_hypothesis(self, state):
        h = state.add_hypothesis("Hyp1", 0.5, hypothesis_id="h1")
        assert state.get_hypothesis("h1") is h

    def test_get_hypothesis_nonexistent(self, state):
        assert state.get_hypothesis("nope") is None

    def test_update_hypothesis_text(self, state):
        state.add_hypothesis("Old text", 0.5, hypothesis_id="h1")
        state.update_hypothesis("h1", new_text="New text")
        assert state.get_hypothesis("h1")["text"] == "New text"

    def test_update_hypothesis_confidence(self, state):
        state.add_hypothesis("Hyp", 0.5, hypothesis_id="h1")
        state.update_hypothesis("h1", new_confidence=0.9)
        assert state.get_hypothesis("h1")["confidence_score"] == 0.9

    def test_update_hypothesis_status(self, state):
        state.add_hypothesis("Hyp", 0.5, hypothesis_id="h1")
        state.update_hypothesis("h1", new_status="confirmed")
        assert state.get_hypothesis("h1")["status"] == "confirmed"

    def test_update_hypothesis_add_evidence(self, state):
        state.add_hypothesis("Hyp", 0.5, hypothesis_id="h1")
        state.update_hypothesis("h1", add_supporting_evidence_id="e1")
        state.update_hypothesis("h1", add_contradicting_evidence_id="e2")
        h = state.get_hypothesis("h1")
        assert "e1" in h["supporting_evidence_ids"]
        assert "e2" in h["contradicting_evidence_ids"]

    def test_update_hypothesis_nonexistent(self, state):
        assert state.update_hypothesis("nope", new_text="x") is False

    def test_get_hypotheses_all(self, state):
        state.add_hypothesis("H1", 0.5)
        state.add_hypothesis("H2", 0.7)
        assert len(state.get_hypotheses()) == 2

    def test_get_hypotheses_by_status(self, state):
        state.add_hypothesis("H1", 0.5, hypothesis_id="h1")
        state.add_hypothesis("H2", 0.7, hypothesis_id="h2")
        state.update_hypothesis("h1", new_status="confirmed")
        assert len(state.get_hypotheses(status="confirmed")) == 1


# ── EnqueteCluedoState ──


class TestEnqueteCluedoState:
    @pytest.fixture
    def elements(self):
        return {
            "suspects": ["Colonel Mustard", "Miss Scarlet", "Professor Plum"],
            "armes": ["Rope", "Candlestick", "Knife"],
            "lieux": ["Kitchen", "Library", "Ballroom"],
        }

    @pytest.fixture
    def solution(self):
        return {"suspect": "Colonel Mustard", "arme": "Rope", "lieu": "Kitchen"}

    @pytest.fixture
    def state(self, elements, solution):
        return EnqueteCluedoState(
            "Cluedo Game",
            elements,
            "A murder in the mansion",
            {"game": True},
            solution_secrete_cluedo=solution,
        )

    def test_init_with_solution(self, state, solution):
        assert state.nom_enquete_cluedo == "Cluedo Game"
        assert state.solution_secrete_cluedo == solution
        assert state.is_solution_proposed is False
        assert state.final_solution is None

    def test_init_auto_solution(self, elements):
        state = EnqueteCluedoState("Auto Game", elements, "Murder case", {})
        sol = state.solution_secrete_cluedo
        assert sol["suspect"] in elements["suspects"]
        assert sol["arme"] in elements["armes"]
        assert sol["lieu"] in elements["lieux"]

    def test_init_no_solution_no_auto_raises(self, elements):
        with pytest.raises(ValueError):
            EnqueteCluedoState(
                "Game",
                elements,
                "desc",
                {},
                solution_secrete_cluedo=None,
                auto_generate_solution=False,
            )

    def test_init_empty_suspects_raises(self):
        elements = {"suspects": [], "armes": ["Knife"], "lieux": ["Kitchen"]}
        with pytest.raises(ValueError, match="suspects"):
            EnqueteCluedoState("Game", elements, "desc", {})

    def test_init_empty_armes_raises(self):
        elements = {"suspects": ["Col. Mustard"], "armes": [], "lieux": ["Kitchen"]}
        with pytest.raises(ValueError, match="armes"):
            EnqueteCluedoState("Game", elements, "desc", {})

    def test_init_empty_lieux_raises(self):
        elements = {"suspects": ["Col. Mustard"], "armes": ["Knife"], "lieux": []}
        with pytest.raises(ValueError, match="lieux"):
            EnqueteCluedoState("Game", elements, "desc", {})

    def test_get_solution_secrete(self, state, solution):
        assert state.get_solution_secrete() == solution

    def test_get_elements_jeu(self, state, elements):
        assert state.get_elements_jeu() == elements

    def test_belief_set_initialized(self, state):
        bs = state.belief_set_initial_watson
        # Two suspects excluded (not Colonel Mustard)
        assert len(bs["suspects_exclus"]) == 2
        # Two weapons excluded (not Rope)
        assert len(bs["armes_exclues"]) == 2
        # Two locations excluded (not Kitchen)
        assert len(bs["lieux_exclus"]) == 2

    def test_main_belief_set_exists(self, state):
        content = state.get_belief_set_content(state.main_cluedo_bs_id)
        assert content is not None
        assert "Not(Coupable(" in content

    def test_propose_final_solution(self, state):
        state.propose_final_solution(
            {"suspect": "Miss Scarlet", "arme": "Knife", "lieu": "Library"}
        )
        assert state.is_solution_proposed is True
        assert state.final_solution["suspect"] == "Miss Scarlet"

    def test_propose_invalid_solution(self, state):
        with pytest.raises(ValueError):
            state.propose_final_solution({"suspect": "X"})

    def test_inherits_base_functionality(self, state):
        # Can use BaseWorkflowState task methods
        task = state.add_task("Investigate", "watson")
        assert task["assignee"] == "watson"
        # Can use EnquetePoliciereState hypothesis methods
        h = state.add_hypothesis("Butler did it", 0.7)
        assert h["text"] == "Butler did it"
