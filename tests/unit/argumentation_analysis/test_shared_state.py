# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module shared_state.
"""

import unittest
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState


class TestRhetoricalAnalysisState(unittest.TestCase):
    """Tests pour la classe RhetoricalAnalysisState."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.initial_text = "Ceci est un texte de test pour l'analyse rhétorique."
        self.state = RhetoricalAnalysisState(self.initial_text)

    def test_initialization(self):
        """Teste l'initialisation correcte de l'état."""
        self.assertEqual(self.state.raw_text, self.initial_text)
        self.assertEqual(self.state.analysis_tasks, {})
        self.assertEqual(self.state.identified_arguments, {})
        self.assertEqual(self.state.identified_fallacies, {})
        self.assertEqual(self.state.belief_sets, {})
        self.assertEqual(self.state.query_log, [])
        self.assertEqual(self.state.answers, {})
        self.assertIsNone(self.state.final_conclusion)
        self.assertIsNone(self.state._next_agent_designated)

    def test_add_task(self):
        """Teste l'ajout d'une tâche."""
        task_description = "Analyser les arguments principaux"
        task_id = self.state.add_task(task_description)

        # Vérifier que l'ID commence par "task_"
        self.assertTrue(task_id.startswith("task_"))

        # Vérifier que la tâche a été ajoutée correctement
        self.assertIn(task_id, self.state.analysis_tasks)
        self.assertEqual(self.state.analysis_tasks[task_id], task_description)

    def test_add_argument(self):
        """Teste l'ajout d'un argument."""
        arg_description = "La Terre est ronde car on peut en faire le tour"
        arg_id = self.state.add_argument(arg_description)

        # Vérifier que l'ID commence par "arg_"
        self.assertTrue(arg_id.startswith("arg_"))

        # Vérifier que l'argument a été ajouté correctement
        self.assertIn(arg_id, self.state.identified_arguments)
        self.assertEqual(self.state.identified_arguments[arg_id], arg_description)

    def test_add_fallacy(self):
        """Teste l'ajout d'un sophisme."""
        fallacy_type = "Ad Hominem"
        justification = "Attaque la personne plutôt que l'argument"
        fallacy_id = self.state.add_fallacy(fallacy_type, justification)

        # Vérifier que l'ID commence par "fallacy_"
        self.assertTrue(fallacy_id.startswith("fallacy_"))

        # Vérifier que le sophisme a été ajouté correctement
        self.assertIn(fallacy_id, self.state.identified_fallacies)
        self.assertEqual(
            self.state.identified_fallacies[fallacy_id]["type"], fallacy_type
        )
        self.assertEqual(
            self.state.identified_fallacies[fallacy_id]["justification"], justification
        )
        self.assertNotIn(
            "target_argument_id", self.state.identified_fallacies[fallacy_id]
        )

    def test_add_fallacy_with_target(self):
        """Teste l'ajout d'un sophisme avec un argument cible."""
        # Ajouter d'abord un argument
        arg_description = "La Terre est ronde car on peut en faire le tour"
        arg_id = self.state.add_argument(arg_description)

        # Ajouter un sophisme ciblant cet argument
        fallacy_type = "Ad Hominem"
        justification = "Attaque la personne plutôt que l'argument"
        fallacy_id = self.state.add_fallacy(fallacy_type, justification, arg_id)

        # Vérifier que le sophisme a été ajouté correctement avec la cible
        self.assertIn(fallacy_id, self.state.identified_fallacies)
        self.assertEqual(
            self.state.identified_fallacies[fallacy_id]["type"], fallacy_type
        )
        self.assertEqual(
            self.state.identified_fallacies[fallacy_id]["justification"], justification
        )
        self.assertEqual(
            self.state.identified_fallacies[fallacy_id]["target_argument_id"], arg_id
        )

    def test_add_belief_set(self):
        """Teste l'ajout d'un belief set."""
        logic_type = "Propositional"
        content = "a => b\nb => c\na"
        bs_id = self.state.add_belief_set(logic_type, content)

        # Vérifier que l'ID commence par "propositional_bs_"
        self.assertTrue(bs_id.startswith("propositional_bs_"))

        # Vérifier que le belief set a été ajouté correctement
        self.assertIn(bs_id, self.state.belief_sets)
        self.assertEqual(self.state.belief_sets[bs_id]["logic_type"], logic_type)
        self.assertEqual(self.state.belief_sets[bs_id]["content"], content)

    def test_log_query(self):
        """Teste l'enregistrement d'une requête."""
        # Ajouter d'abord un belief set
        logic_type = "Propositional"
        content = "a => b\nb => c\na"
        bs_id = self.state.add_belief_set(logic_type, content)

        # Enregistrer une requête
        query = "a => c"
        raw_result = "ACCEPTED (True)"
        log_id = self.state.log_query(bs_id, query, raw_result)

        # Vérifier que l'ID commence par "qlog_"
        self.assertTrue(log_id.startswith("qlog_"))

        # Vérifier que la requête a été enregistrée correctement
        self.assertEqual(len(self.state.query_log), 1)
        self.assertEqual(self.state.query_log[0]["log_id"], log_id)
        self.assertEqual(self.state.query_log[0]["belief_set_id"], bs_id)
        self.assertEqual(self.state.query_log[0]["query"], query)
        self.assertEqual(self.state.query_log[0]["raw_result"], raw_result)

    def test_add_answer(self):
        """Teste l'ajout d'une réponse."""
        # Ajouter d'abord une tâche
        task_description = "Analyser les arguments principaux"
        task_id = self.state.add_task(task_description)

        # Ajouter une réponse
        author_agent = "InformalAnalysisAgent"
        answer_text = "Les arguments principaux sont..."
        source_ids = ["arg_1", "arg_2"]
        self.state.add_answer(task_id, author_agent, answer_text, source_ids)

        # Vérifier que la réponse a été ajoutée correctement
        self.assertIn(task_id, self.state.answers)
        self.assertEqual(self.state.answers[task_id]["author_agent"], author_agent)
        self.assertEqual(self.state.answers[task_id]["answer_text"], answer_text)
        self.assertEqual(self.state.answers[task_id]["source_ids"], source_ids)

    def test_set_conclusion(self):
        """Teste la définition de la conclusion finale."""
        conclusion = "L'analyse montre que les arguments sont valides."
        self.state.set_conclusion(conclusion)

        # Vérifier que la conclusion a été définie correctement
        self.assertEqual(self.state.final_conclusion, conclusion)

    def test_designate_next_agent(self):
        """Teste la désignation du prochain agent."""
        agent_name = "PropositionalLogicAgent"
        self.state.designate_next_agent(agent_name)

        # Vérifier que l'agent a été désigné correctement
        self.assertEqual(self.state._next_agent_designated, agent_name)

        # Consommer la désignation
        consumed_agent = self.state.consume_next_agent_designation()

        # Vérifier que la désignation a été consommée correctement
        self.assertEqual(consumed_agent, agent_name)
        self.assertIsNone(self.state._next_agent_designated)

    def test_reset_state(self):
        """Teste la réinitialisation de l'état."""
        # Ajouter quelques données à l'état
        self.state.add_task("Tâche de test")
        self.state.add_argument("Argument de test")
        self.state.add_fallacy("Sophisme", "Justification")
        self.state.add_belief_set("Propositional", "a => b")
        self.state.set_conclusion("Conclusion de test")

        # Réinitialiser l'état
        self.state.reset_state()

        # Vérifier que l'état a été réinitialisé correctement
        self.assertEqual(self.state.raw_text, self.initial_text)
        self.assertEqual(self.state.analysis_tasks, {})
        self.assertEqual(self.state.identified_arguments, {})
        self.assertEqual(self.state.identified_fallacies, {})
        self.assertEqual(self.state.belief_sets, {})
        self.assertEqual(self.state.query_log, [])
        self.assertEqual(self.state.answers, {})
        self.assertIsNone(self.state.final_conclusion)
        self.assertIsNone(self.state._next_agent_designated)

    def test_to_json(self):
        """Teste la sérialisation en JSON."""
        # Ajouter quelques données à l'état
        self.state.add_task("Tâche de test")
        self.state.add_argument("Argument de test")

        # Sérialiser l'état en JSON
        json_str = self.state.to_json(indent=None)

        # Vérifier que la chaîne JSON est valide et contient les données attendues
        self.assertIn("raw_text", json_str)
        self.assertIn("analysis_tasks", json_str)
        self.assertIn("identified_arguments", json_str)

    def test_from_dict(self):
        """Teste la création d'un état à partir d'un dictionnaire."""
        # Créer un dictionnaire de données
        data = {
            "raw_text": "Texte de test",
            "analysis_tasks": {"task_1": "Tâche 1"},
            "identified_arguments": {"arg_1": "Argument 1"},
            "identified_fallacies": {
                "fallacy_1": {"type": "Sophisme 1", "justification": "Justification 1"}
            },
            "belief_sets": {
                "bs_1": {"logic_type": "Propositional", "content": "a => b"}
            },
            "query_log": [
                {
                    "log_id": "qlog_1",
                    "belief_set_id": "bs_1",
                    "query": "a => b",
                    "raw_result": "ACCEPTED",
                }
            ],
            "answers": {
                "task_1": {
                    "author_agent": "Agent",
                    "answer_text": "Réponse",
                    "source_ids": ["arg_1"],
                }
            },
            "final_conclusion": "Conclusion finale",
            "_next_agent_designated": "Agent",
        }

        # Créer un état à partir du dictionnaire
        state = RhetoricalAnalysisState.from_dict(data)

        # Vérifier que l'état a été créé correctement
        self.assertEqual(state.raw_text, data["raw_text"])
        self.assertEqual(state.analysis_tasks, data["analysis_tasks"])
        self.assertEqual(state.identified_arguments, data["identified_arguments"])
        self.assertEqual(state.identified_fallacies, data["identified_fallacies"])
        self.assertEqual(state.belief_sets, data["belief_sets"])
        self.assertEqual(state.query_log, data["query_log"])
        self.assertEqual(state.answers, data["answers"])
        self.assertEqual(state.final_conclusion, data["final_conclusion"])
        self.assertEqual(state._next_agent_designated, data["_next_agent_designated"])


# ===========================================================================
# UnifiedAnalysisState (Phase 4 Extensions)
# ===========================================================================


class TestUnifiedAnalysisState(unittest.TestCase):
    """Tests for UnifiedAnalysisState — Phase 4 extended dimensions."""

    def setUp(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        self.state = UnifiedAnalysisState("Texte pour analyse unifiée.")

    def test_inherits_from_rhetorical(self):
        """UnifiedAnalysisState is a RhetoricalAnalysisState."""
        self.assertIsInstance(self.state, RhetoricalAnalysisState)

    def test_initial_extended_fields_empty(self):
        """All Phase 4 fields start empty."""
        self.assertEqual(self.state.counter_arguments, [])
        self.assertEqual(self.state.argument_quality_scores, {})
        self.assertEqual(self.state.jtms_beliefs, {})
        self.assertEqual(self.state.dung_frameworks, {})
        self.assertEqual(self.state.governance_decisions, [])
        self.assertEqual(self.state.debate_transcripts, [])
        self.assertEqual(self.state.transcription_segments, [])
        self.assertEqual(self.state.semantic_index_refs, [])
        self.assertEqual(self.state.neural_fallacy_scores, [])
        self.assertEqual(self.state.workflow_results, {})

    # --- Counter-arguments (2.3.3) ---

    def test_add_counter_argument(self):
        ca_id = self.state.add_counter_argument(
            original_arg="Le ciel est bleu",
            counter_content="La nuit le ciel est noir",
            strategy="counter_example",
            score=0.85,
        )
        self.assertTrue(ca_id.startswith("ca_"))
        self.assertEqual(len(self.state.counter_arguments), 1)
        entry = self.state.counter_arguments[0]
        self.assertEqual(entry["id"], ca_id)
        self.assertEqual(entry["original_argument"], "Le ciel est bleu")
        self.assertEqual(entry["strategy"], "counter_example")
        self.assertAlmostEqual(entry["score"], 0.85)

    def test_add_multiple_counter_arguments(self):
        id1 = self.state.add_counter_argument("A", "not A", "reductio", 0.7)
        id2 = self.state.add_counter_argument("B", "not B", "distinction", 0.9)
        self.assertNotEqual(id1, id2)
        self.assertEqual(len(self.state.counter_arguments), 2)

    # --- Quality scores (2.3.5) ---

    def test_add_quality_score(self):
        self.state.add_quality_score(
            arg_id="arg_1",
            scores={"clarity": 0.8, "coherence": 0.9},
            overall=0.85,
        )
        self.assertIn("arg_1", self.state.argument_quality_scores)
        entry = self.state.argument_quality_scores["arg_1"]
        self.assertEqual(entry["overall"], 0.85)
        self.assertEqual(entry["scores"]["clarity"], 0.8)

    def test_quality_score_overwrites(self):
        """Adding a score for the same arg_id overwrites the previous one."""
        self.state.add_quality_score("arg_1", {"clarity": 0.5}, 0.5)
        self.state.add_quality_score("arg_1", {"clarity": 0.9}, 0.9)
        self.assertEqual(self.state.argument_quality_scores["arg_1"]["overall"], 0.9)

    # --- JTMS beliefs (1.4.1) ---

    def test_add_jtms_belief(self):
        belief_id = self.state.add_jtms_belief(
            name="rain", valid=True, justifications=["clouds", "humidity"]
        )
        self.assertTrue(belief_id.startswith("jtms_"))
        self.assertIn(belief_id, self.state.jtms_beliefs)
        entry = self.state.jtms_beliefs[belief_id]
        self.assertEqual(entry["name"], "rain")
        self.assertTrue(entry["valid"])
        self.assertEqual(entry["justifications"], ["clouds", "humidity"])

    def test_add_jtms_belief_none_valid(self):
        """JTMS beliefs can have valid=None (undetermined)."""
        belief_id = self.state.add_jtms_belief("mystery", valid=None, justifications=[])
        self.assertIsNone(self.state.jtms_beliefs[belief_id]["valid"])

    # --- Dung frameworks (abs_arg_dung) ---

    def test_add_dung_framework(self):
        df_id = self.state.add_dung_framework(
            name="simple_framework",
            arguments=["a", "b", "c"],
            attacks=[["a", "b"], ["b", "c"]],
            extensions={"grounded": ["a", "c"]},
        )
        self.assertTrue(df_id.startswith("dung_"))
        self.assertIn(df_id, self.state.dung_frameworks)
        entry = self.state.dung_frameworks[df_id]
        self.assertEqual(entry["name"], "simple_framework")
        self.assertEqual(len(entry["arguments"]), 3)
        self.assertEqual(len(entry["attacks"]), 2)
        self.assertEqual(entry["extensions"]["grounded"], ["a", "c"])

    def test_add_dung_framework_no_extensions(self):
        """Extensions default to empty dict when not provided."""
        df_id = self.state.add_dung_framework(
            name="minimal", arguments=["x"], attacks=[]
        )
        self.assertEqual(self.state.dung_frameworks[df_id]["extensions"], {})

    # --- Governance decisions (2.1.6) ---

    def test_add_governance_decision(self):
        gd_id = self.state.add_governance_decision(
            method="majority",
            winner="option_A",
            scores={"option_A": 5, "option_B": 3},
        )
        self.assertTrue(gd_id.startswith("gov_"))
        self.assertEqual(len(self.state.governance_decisions), 1)
        entry = self.state.governance_decisions[0]
        self.assertEqual(entry["method"], "majority")
        self.assertEqual(entry["winner"], "option_A")
        self.assertEqual(entry["scores"]["option_A"], 5)

    # --- Debate transcripts (1.2.7) ---

    def test_add_debate_transcript(self):
        dt_id = self.state.add_debate_transcript(
            topic="Should AI be regulated?",
            exchanges=[
                {"agent": "Scholar", "content": "Yes, because..."},
                {"agent": "Diplomat", "content": "No, because..."},
            ],
            winner="Scholar",
        )
        self.assertTrue(dt_id.startswith("debate_"))
        self.assertEqual(len(self.state.debate_transcripts), 1)
        entry = self.state.debate_transcripts[0]
        self.assertEqual(entry["topic"], "Should AI be regulated?")
        self.assertEqual(len(entry["exchanges"]), 2)
        self.assertEqual(entry["winner"], "Scholar")

    def test_add_debate_transcript_no_winner(self):
        dt_id = self.state.add_debate_transcript(
            topic="Draw debate", exchanges=[], winner=None
        )
        self.assertIsNone(self.state.debate_transcripts[0]["winner"])

    # --- Workflow results ---

    def test_set_workflow_results(self):
        self.state.set_workflow_results("light", {"phases": 3, "status": "complete"})
        self.assertIn("light", self.state.workflow_results)
        self.assertEqual(self.state.workflow_results["light"]["status"], "complete")

    def test_set_multiple_workflow_results(self):
        self.state.set_workflow_results("light", {"status": "ok"})
        self.state.set_workflow_results("full", {"status": "ok"})
        self.assertEqual(len(self.state.workflow_results), 2)

    # --- get_state_snapshot (summarize) ---

    def test_snapshot_summarize_includes_extended_counts(self):
        """Summarized snapshot includes all Phase 4 dimension counts."""
        self.state.add_counter_argument("a", "b", "s", 0.5)
        self.state.add_quality_score("arg_1", {}, 0.8)
        self.state.add_jtms_belief("b", True, [])
        self.state.add_dung_framework("f", ["x"], [])
        self.state.add_governance_decision("borda", "x", {})
        self.state.add_debate_transcript("t", [])

        snapshot = self.state.get_state_snapshot(summarize=True)
        self.assertEqual(snapshot["counter_argument_count"], 1)
        self.assertEqual(snapshot["quality_scores_count"], 1)
        self.assertEqual(snapshot["jtms_belief_count"], 1)
        self.assertEqual(snapshot["dung_framework_count"], 1)
        self.assertEqual(snapshot["governance_decision_count"], 1)
        self.assertEqual(snapshot["debate_transcript_count"], 1)

    def test_snapshot_full_includes_extended_data(self):
        """Full snapshot includes actual Phase 4 data."""
        self.state.add_counter_argument("a", "b", "s", 0.5)
        snapshot = self.state.get_state_snapshot(summarize=False)
        self.assertIn("counter_arguments", snapshot)
        self.assertEqual(len(snapshot["counter_arguments"]), 1)


if __name__ == "__main__":
    unittest.main()
