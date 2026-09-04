# Cartographie des Tests Notables du Projet

Ce document synthétise les tests les plus représentatifs des fonctionnalités clés du projet. Il a pour but de faciliter la compréhension du code et d'enrichir le script de démonstration principal.

## 1. Génération de Visualisations (`visualization_generator`)

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
## 2. Orchestration Tactique Avancée (`coordinator`)

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

## 3. Analyse de Sophismes Complexes (`enhanced_complex_fallacy_analyzer`)

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