# Cartographie des Tests Notables du Projet

Ce document synthétise les tests les plus représentatifs des fonctionnalités clés du projet. Il a pour but de faciliter la compréhension du code et d'enrichir le script de démonstration principal.

## 1. Analyse de la Cohérence (`coherence_analysis`)

Ces tests valident la capacité du système à évaluer la cohérence logique et structurelle d'un texte.

### Test de la simulation de l'analyse de cohérence

*   **Fichier :** [`tests/unit/argumentation_analysis/mocks/test_coherence_analysis.py`](tests/unit/argumentation_analysis/mocks/test_coherence_analysis.py)
*   **Fonction :** `test_analyze_coherence_multiple_factors_and_clamping()`
*   **Description :** Ce test est crucial car il vérifie le cumul de plusieurs facteurs (mots de transition, répétition de mots-clés, contradictions) pour calculer le score de cohérence. Il s'assure également que le score final est bien "clampé" (limité) dans l'intervalle [0, 1], garantissant ainsi la robustesse du calcul.
*   **Extrait de code :**
    ```python
    def test_analyze_coherence_multiple_factors_and_clamping(analyzer_default: MockCoherenceAnalyzer):
        """Teste le cumul de facteurs et le clampage."""
        text = "J'aime ce test. Donc, c'est un bon test. Cependant, je n'aime pas toujours ce test."
        result = analyzer_default.analyze_coherence(text)
        assert result["coherence_score"] == pytest.approx(0.5 + 0.1 + 0.2 - 0.4)
        assert result["interpretation"] == "Peu cohérent (Mock)"

        # Test clamp à 0
        text_very_incoherent = "J'aime ça. C'est vrai. Mais je n'aime pas ça. Et c'est faux."
        result_bad = analyzer_default.analyze_coherence(text_very_incoherent)
        assert result_bad["coherence_score"] == 0.0
        assert result_bad["interpretation"] == "Incohérent (Mock)"
    ```

## 2. Évaluation de la Clarté (`clarity_scoring`)

Ces tests s'assurent que le système peut noter la clarté d'un texte en pénalisant le jargon, les phrases longues et l'ambiguïté.

### Test de la simulation de l'évaluation de clarté

*   **Fichier :** [`tests/unit/argumentation_analysis/mocks/test_clarity_scoring.py`](tests/unit/argumentation_analysis/mocks/test_clarity_scoring.py)
*   **Fonction :** `test_score_clarity_multiple_penalties_and_clamping()`
*   **Description :** Ce test valide l'accumulation de différentes pénalités (jargon, ambiguïté, etc.) sur le score de clarté. Il confirme que le score final ne peut pas être négatif, ce qui est essentiel pour la fiabilité de la métrique.
*   **Extrait de code :**
    ```python
    def test_score_clarity_multiple_penalties_and_clamping(scorer_default: MockClarityScorer):
        """Teste le cumul de plusieurs pénalités et le clampage à 0."""
        text = (
            "La synergie holistique de ce projet disruptif est peut-être la clé. "
            "Possiblement, certains résultats, quelques indicateurs, le montreront."
        )
        result = scorer_default.score_clarity(text)
        assert result["clarity_score"] == 0.0
        assert result["factors"]["jargon_count"] == 3
        assert result["factors"]["ambiguity_keywords"] == 4
        assert result["interpretation"] == "Pas clair du tout (Mock)"
    ```

## 3. Extraction d'Arguments (`argument_mining`)

Ces tests vérifient la capacité du système à identifier et extraire des structures argumentatives (prémisses, conclusions) d'un texte.

### Test de la simulation de l'extraction d'arguments

*   **Fichier :** [`tests/unit/argumentation_analysis/mocks/test_argument_mining.py`](tests/unit/argumentation_analysis/mocks/test_argument_mining.py)
*   **Fonction :** `test_mine_arguments_complex_scenario_mixed()`
*   **Description :** Ce test démontre la capacité du `MockArgumentMiner` à traiter un texte contenant à la fois des arguments explicites (avec les marqueurs "Prémisse:"/"Conclusion:") et des arguments implicites (basés sur des connecteurs logiques comme "par conséquent"). Il s'assure que les deux types sont correctement identifiés dans un même passage.
*   **Extrait de code :**
    ```python
    def test_mine_arguments_complex_scenario_mixed(miner_default: MockArgumentMiner):
        """Teste un scénario mixte avec explicite et implicite."""
        text = (
            "Prémisse: Le ciel est bleu. Conclusion: C'est une belle journée. "
            "Le soleil brille fortement, par conséquent il fait chaud."
        )
        result = miner_default.mine_arguments(text)
        assert len(result) == 2
    ```

## 4. Génération de Visualisations (`visualization_generator`)

Ces tests garantissent que les rapports visuels sur les performances des agents peuvent être générés correctement.

### Test de la génération des fichiers de visualisation

*   **Fichier :** [`tests/unit/argumentation_analysis/utils/test_visualization_generator.py`](tests/unit/argumentation_analysis/utils/test_visualization_generator.py)
*   **Fonction :** `test_generate_performance_visualizations_files_created()`
*   **Description :** Ce test simule la génération de toutes les visualisations de performance. Il vérifie que la fonction tente de créer les fichiers graphiques (PNG) et le résumé CSV attendus, assurant que le pipeline de reporting visuel est fonctionnel.
*   **Extrait de code :**
    ```python
    @mock.patch('argumentation_analysis.utils.visualization_generator.VISUALIZATION_LIBS_AVAILABLE', True)
    @mock.patch('matplotlib.pyplot.savefig')
    @mock.patch('argumentation_analysis.utils.visualization_generator.pd.DataFrame.to_csv')
    def test_generate_performance_visualizations_files_created(
        mock_df_to_csv, mock_plt_savefig,
        sample_metrics_for_visualization: Dict[str, Dict[str, Any]],
        tmp_path: Path,
        setup_numpy_for_tests_fixture
    ):
        """
        Teste que la fonction tente de créer les fichiers attendus lorsque les bibliothèques sont (supposément) disponibles.
        """
        output_dir = tmp_path / "viz_output_libs_available"
        generated_files = generate_performance_visualizations(sample_metrics_for_visualization, output_dir)

        assert output_dir.exists()
## 5. Orchestration Tactique Avancée (`coordinator`)

Ces tests valident la capacité du coordinateur tactique à gérer des scénarios complexes, notamment la décomposition d'objectifs et l'adaptation aux ajustements stratégiques.

### Test de la décomposition d'objectifs stratégiques

*   **Fichier :** [`tests/orchestration/tactical/test_tactical_coordinator_advanced.py`](tests/orchestration/tactical/test_tactical_coordinator_advanced.py)
*   **Fonction :** `test_process_strategic_objectives()`
*   **Description :** Ce test est fondamental pour comprendre la logique du coordinateur tactique. Il simule la réception d'objectifs de haut niveau (stratégiques) et vérifie que le coordinateur les décompose correctement en tâches opérationnelles plus petites, établit leurs dépendances et les assigne aux agents appropriés. Cela illustre le cœur de la mécanique d'orchestration.
*   **Extrait de code :**
    ```python
    def test_process_strategic_objectives(self):
        """Teste la méthode process_strategic_objectives."""
        # Créer des objectifs stratégiques
        objectives = [
            {
                "id": "obj-1",
                "description": "Identifier les arguments dans le texte",
                "priority": "high",
                "text": "Ceci est un texte d'exemple pour l'analyse des arguments.",
                "type": "argument_identification"
            },
            # ... (autre objectif)
        ]
        
        # Patcher les méthodes appelées par process_strategic_objectives
        with patch.object(self.coordinator, '_decompose_objective_to_tasks') as mock_decompose, \
             patch.object(self.coordinator, '_establish_task_dependencies') as mock_establish, \
             patch.object(self.coordinator, '_assign_task_to_operational_agent') as mock_assign:
            
            # Appeler la méthode process_strategic_objectives
            result = self.coordinator.process_strategic_objectives(objectives)
            
            # Vérifier que les méthodes ont été appelées
            self.assertEqual(mock_decompose.call_count, 2)
            mock_establish.assert_called_once()
            self.assertEqual(mock_assign.call_count, 4)
            self.assertEqual(len(self.tactical_state.assigned_objectives), 2)
    ```

## 6. Analyse de Sophismes Complexes (`enhanced_complex_fallacy_analyzer`)

Ces tests démontrent la capacité du système à identifier des schémas de sophismes sophistiqués et des combinaisons de plusieurs types de sophismes.

### Test de la détection de sophismes composés

*   **Fichier :** [`tests/unit/argumentation_analysis/test_enhanced_complex_fallacy_analyzer.py`](tests/unit/argumentation_analysis/test_enhanced_complex_fallacy_analyzer.py)
*   **Fonction :** `test_detect_composite_fallacies()`
*   **Description :** Ce test met en évidence la capacité du système à aller au-delà de la simple détection de sophismes individuels. Il vérifie que l'analyseur peut identifier des combinaisons de sophismes et des schémas fallacieux complexes, offrant ainsi une analyse beaucoup plus fine et profonde de l'argumentation.
*   **Extrait de code :**
    ```python
    def test_detect_composite_fallacies(
        self,
        mock_evaluate_severity,
        mock_identify_patterns,
        mock_identify_advanced,
        mock_identify_combined,
        mock_contextual_analyzer
    ):
        """Teste la détection des sophismes composés."""
        # Configurer les mocks
        mock_contextual_analyzer.identify_contextual_fallacies.return_value = [
            {"fallacy_type": "Appel à l'autorité", "confidence": 0.8}
        ]
        mock_identify_combined.return_value = [{"combination_type": "autorité_popularité", "severity": 0.7}]
        mock_identify_advanced.return_value = [{"combination_name": "cercle_autoritaire", "severity": 0.8}]
        
        # Appeler la méthode à tester
        result = self.analyzer.detect_composite_fallacies(self.test_arguments, self.test_context)
        
        # Vérifier les résultats
        self.assertIn("individual_fallacies_count", result)
        self.assertIn("basic_combinations", result)
        self.assertIn("advanced_combinations", result)
    ```