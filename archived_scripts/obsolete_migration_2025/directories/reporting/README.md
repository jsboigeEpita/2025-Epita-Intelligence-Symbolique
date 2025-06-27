# Scripts de Reporting

Ce répertoire contient des scripts utilisés pour générer divers rapports et visualisations concernant le projet.
Il contient également des README spécifiques à certains rapports, comme [`README_compare_rhetorical_agents.md`](scripts/reporting/README_compare_rhetorical_agents.md:1).

## Scripts

- `compare_rhetorical_agents.py`: Script complet pour comparer les performances des différents agents d'analyse rhétorique. Il charge les résultats, calcule de nombreuses métriques, génère des visualisations et un rapport détaillé.
- `compare_rhetorical_agents_simple.py`: Version simplifiée du script de comparaison des agents. **Note : Ce script est potentiellement redondant avec `compare_rhetorical_agents.py` et pourrait être fusionné ou supprimé après évaluation.**
- `generate_comprehensive_report.py`: Génère un rapport complet sur l'état du projet.
- `generate_coverage_report.py`: Génère un rapport sur la couverture des tests.
- `generate_rhetorical_analysis_summaries.py`: Génère des résumés des analyses rhétoriques.
- `initialize_coverage_history.py`: Initialise l'historique de couverture des tests, utilisé par d'autres scripts de reporting.
- `update_coverage_in_report.py`: Met à jour la section de couverture dans un fichier de rapport (anciennement `scripts/reports/update_coverage_section.py`).
- `update_main_report_file.py`: Met à jour le fichier de rapport principal (anciennement `scripts/reports/update_final_report.py`).
- `visualize_test_coverage.py`: Crée des visualisations pour le rapport de couverture des tests.