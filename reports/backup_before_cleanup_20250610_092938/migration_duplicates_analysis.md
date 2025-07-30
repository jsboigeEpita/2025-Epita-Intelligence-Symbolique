# Rapport d'Analyse des Doublons de Migration

**Généré le** : 2025-06-10T09:25:01.538954

## Résumé Exécutif

- **Fichiers dans scripts/** : 350
- **Fichiers dans archived/** : 36
- **Doublons exacts** : 35
- **Doublons modifiés** : 0
- **Fichiers uniques scripts/** : 315
- **Fichiers uniques archived/** : 1

## Recommandations d'Action

- **🗑️ SUPPRIMER** : 32 fichiers
- **✅ CONSERVER** : 0 fichiers
- **⚠️ ÉVALUER** : 3 fichiers

## Analyse Détaillée des Doublons

### 🗑️ Action Recommandée : SUPPRIMER

#### `analyze_phase2_by_groups.py`

- **Statut** : EXACT
- **Taille** : scripts=4815B, archived=4815B (diff: +0B)
- **Modification** : +233834.9s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `authentic_tests_validation.py`

- **Statut** : EXACT
- **Taille** : scripts=17883B, archived=17883B (diff: +0B)
- **Modification** : +76886.4s après archivage
- **Références** : 1 trouvées
- **Justification** : Doublon exact avec seulement 1 références mineures

**Fichiers référençant** :
  - `scripts\final_system_integration_test.py`

#### `auto_logical_analysis_task1.py`

- **Statut** : EXACT
- **Taille** : scripts=29959B, archived=29959B (diff: +0B)
- **Modification** : +36091.4s après archivage
- **Références** : 1 trouvées
- **Justification** : Doublon exact avec seulement 1 références mineures

**Fichiers référençant** :
  - `scripts\auto_logical_analysis_task1_VRAI.py`

#### `auto_logical_analysis_task1_fixed.py`

- **Statut** : EXACT
- **Taille** : scripts=31526B, archived=31526B (diff: +0B)
- **Modification** : +35943.0s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `auto_logical_analysis_task1_simple.py`

- **Statut** : EXACT
- **Taille** : scripts=29056B, archived=29056B (diff: +0B)
- **Modification** : +35794.0s après archivage
- **Références** : 1 trouvées
- **Justification** : Doublon exact avec seulement 1 références mineures

**Fichiers référençant** :
  - `scripts\auto_logical_analysis_task1_VRAI.py`

#### `auto_logical_analysis_task1_VRAI.py`

- **Statut** : EXACT
- **Taille** : scripts=33582B, archived=33582B (diff: +0B)
- **Modification** : +35353.0s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `batch_test_analysis.py`

- **Statut** : EXACT
- **Taille** : scripts=7965B, archived=7965B (diff: +0B)
- **Modification** : +233578.0s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `diagnostic_tests_phases.py`

- **Statut** : EXACT
- **Taille** : scripts=5516B, archived=5516B (diff: +0B)
- **Modification** : +134194.8s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `diagnostic_tests_unitaires.py`

- **Statut** : EXACT
- **Taille** : scripts=4502B, archived=4502B (diff: +0B)
- **Modification** : +134247.9s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `final_system_integration_test.py`

- **Statut** : EXACT
- **Taille** : scripts=8353B, archived=8353B (diff: +0B)
- **Modification** : +76048.0s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `fix_asyncio_decorators.py`

- **Statut** : EXACT
- **Taille** : scripts=2770B, archived=2770B (diff: +0B)
- **Modification** : +108846.1s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `fix_critical_imports.py`

- **Statut** : EXACT
- **Taille** : scripts=7857B, archived=7857B (diff: +0B)
- **Modification** : +296796.5s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `fix_return_assert.py`

- **Statut** : EXACT
- **Taille** : scripts=747B, archived=747B (diff: +0B)
- **Modification** : +108846.1s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `fix_unicode_conda.py`

- **Statut** : EXACT
- **Taille** : scripts=3868B, archived=3868B (diff: +0B)
- **Modification** : +296796.5s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `get_env_name.py`

- **Statut** : EXACT
- **Taille** : scripts=2376B, archived=2376B (diff: +0B)
- **Modification** : +448895.0s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `localize_source_contents.py`

- **Statut** : EXACT
- **Taille** : scripts=18787B, archived=18787B (diff: +0B)
- **Modification** : +644422.5s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `measure_final_success_rate.py`

- **Statut** : EXACT
- **Taille** : scripts=19715B, archived=19715B (diff: +0B)
- **Modification** : +232367.8s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `migrate_to_service_manager.py`

- **Statut** : EXACT
- **Taille** : scripts=22448B, archived=22448B (diff: +0B)
- **Modification** : +229064.1s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `minimal_test_diagnostic.py`

- **Statut** : EXACT
- **Taille** : scripts=3367B, archived=3367B (diff: +0B)
- **Modification** : +233637.8s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `phase4_final_validation.py`

- **Statut** : EXACT
- **Taille** : scripts=18394B, archived=18394B (diff: +0B)
- **Modification** : +231974.8s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `populate_extract_segments.py`

- **Statut** : EXACT
- **Taille** : scripts=5512B, archived=5512B (diff: +0B)
- **Modification** : +647794.1s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `populate_full_texts.py`

- **Statut** : EXACT
- **Taille** : scripts=11054B, archived=11054B (diff: +0B)
- **Modification** : +644132.1s après archivage
- **Références** : 1 trouvées
- **Justification** : Doublon exact avec seulement 1 références mineures

**Fichiers référençant** :
  - `scripts\populate_extract_segments.py`

#### `rapport_investigation_tests_unitaires.py`

- **Statut** : EXACT
- **Taille** : scripts=6810B, archived=6810B (diff: +0B)
- **Modification** : +133972.1s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `test_jpype_killer.py`

- **Statut** : EXACT
- **Taille** : scripts=3414B, archived=3414B (diff: +0B)
- **Modification** : +233023.1s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `test_orchestration_scenario.py`

- **Statut** : EXACT
- **Taille** : scripts=11998B, archived=11998B (diff: +0B)
- **Modification** : +76221.1s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `test_practical_capabilities.py`

- **Statut** : EXACT
- **Taille** : scripts=11121B, archived=11121B (diff: +0B)
- **Modification** : +147088.9s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `test_unicode_encoding.py`

- **Statut** : EXACT
- **Taille** : scripts=3573B, archived=3573B (diff: +0B)
- **Modification** : +296796.5s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `validate_new_components_tests.py`

- **Statut** : EXACT
- **Taille** : scripts=13979B, archived=13979B (diff: +0B)
- **Modification** : +147088.9s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `validate_unified_system.py`

- **Statut** : EXACT
- **Taille** : scripts=14693B, archived=14693B (diff: +0B)
- **Modification** : +147088.9s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `validation_point4_rhetorical_analysis.py`

- **Statut** : EXACT
- **Taille** : scripts=30782B, archived=30782B (diff: +0B)
- **Modification** : +41424.5s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `validation_point5_final_comprehensive.py`

- **Statut** : EXACT
- **Taille** : scripts=26358B, archived=26358B (diff: +0B)
- **Modification** : +41057.7s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

#### `validation_point5_realistic_final.py`

- **Statut** : EXACT
- **Taille** : scripts=28746B, archived=28746B (diff: +0B)
- **Modification** : +40908.7s après archivage
- **Références** : 0 trouvées
- **Justification** : Doublon exact sans références actives

### ⚠️ Action Recommandée : ÉVALUER

#### `run_webapp_integration.py`

- **Statut** : EXACT
- **Taille** : scripts=5575B, archived=5575B (diff: +0B)
- **Modification** : +164435.9s après archivage
- **Références** : 3 trouvées
- **Justification** : Doublon exact mais 3 références trouvées

**Fichiers référençant** :
  - `scripts\maintenance\comprehensive_documentation_fixer_safe.py`
  - `scripts\maintenance\quick_documentation_fixer.py`
  - `scripts\webapp\cleanup_redundant_scripts.py`

#### `sprint3_final_validation.py`

- **Statut** : EXACT
- **Taille** : scripts=13814B, archived=13814B (diff: +0B)
- **Modification** : +296796.5s après archivage
- **Références** : 3 trouvées
- **Justification** : Doublon exact mais 3 références trouvées

**Fichiers référençant** :
  - `scripts\webapp\cleanup_redundant_scripts.py`
  - `scripts\webapp\test_orchestrator.py`
  - `scripts\webapp\unified_web_orchestrator.py`

#### `__init__.py`

- **Statut** : EXACT
- **Taille** : scripts=59B, archived=59B (diff: +0B)
- **Modification** : +979251.6s après archivage
- **Références** : 10 trouvées
- **Justification** : Doublon exact mais 10 références trouvées

**Fichiers référençant** :
  - `scripts\validation_point4_rhetorical_analysis.py`
  - `scripts\archived\corrections_complementaires.py`
  - `scripts\cleanup\cleanup_project.py`
  - `scripts\diagnostic\test_validation_environnement.py`
  - `scripts\maintenance\finalize_refactoring.py`
  - `scripts\maintenance\refactor_oracle_system.py`
  - `scripts\maintenance\update_documentation.py`
  - `scripts\setup\adapt_code_for_pyjnius.py`
  - `scripts\setup\fix_environment_auto.py`
  - `scripts\validation\validate_consolidated_system.py`


## Fichiers Orphelins

- `README.md`
- `README_CONFLICT_RESOLUTION.md`
- `README_ORCHESTRATION_CONVERSATION.md`
- `analysis\analyse_trace_cluedo_oracle.py`
- `analysis\analyse_trace_simulated.py`
- `analysis\create_mock_taxonomy_script.py`
- `analysis\generer_cartographie_doc.py`
- `analyze_migration_duplicates.py`
- `apps\backend_info.json`
- `apps\config\webapp_config.yml`
- `apps\start_webapp.py`
- `archived:cleanup_obsolete_scripts.py`
- `archived\README.md`
- `archived\analyse_13_problemes_simple.py`
- `archived\corrections_13_problemes_finales.py`
- `archived\corrections_complementaires.py`
- `archived\diagnostic_13_problemes.py`
- `cleanup\.gitignore`
- `cleanup\README.md`
- `cleanup\README_clean_project.md`
- `cleanup\README_cleanup_redundant.md`
- `cleanup\clean_project.ps1`
- `cleanup\cleanup_obsolete_files.py`
- `cleanup\cleanup_old_agent_dirs.ps1`
- `cleanup\cleanup_project.py`
- `cleanup\cleanup_redundant_files.ps1`
- `cleanup\cleanup_repository.py`
- `cleanup\cleanup_residual_docs.py`
- `cleanup\cleanup_root_final.ps1`
- `cleanup\global_cleanup.py`
- `cleanup\prepare_commit.py`
- `cleanup\reorganize_project.py`
- `consolidated\README.md`
- `consolidated\README_ARCHITECTURE_CENTRALE.md`
- `consolidated\README_comprehensive_workflow.md`
- `consolidated\README_educational_showcase_system.md`
- `consolidated\README_universal_rhetorical_analyzer.md`
- `consolidated\comprehensive_config_example.json`
- `consolidated\comprehensive_workflow_processor.py`
- `consolidated\config_example.json`
- `consolidated\educational_config_example.json`
- `consolidated\educational_showcase_system.py`
- `consolidated\migration_guide.py`
- `consolidated\test_comprehensive_workflow.py`
- `consolidated\test_educational_showcase_simple.py`
- `consolidated\test_educational_showcase_system.py`
- `consolidated\test_unified_analyzer.py`
- `consolidated\test_universal_rhetorical_analyzer.py`
- `consolidated\unified_production_analyzer.py`
- `consolidated\universal_config_example.json`
- `consolidated\universal_rhetorical_analyzer.py`
- `core\README.md`
- `core\__init__.py`
- `core\auto_env.py`
- `core\common_utils.py`
- `core\environment_manager.py`
- `core\load_dotenv.py`
- `core\project_setup.py`
- `core\test_runner.py`
- `core\unified_report_generator.py`
- `core\unified_source_selector.py`
- `core\validation_engine.py`
- `create_readme.ps1`
- `data_processing\README.md`
- `data_processing\auto_correct_markers.py`
- `data_processing\debug_inspect_extract_sources.py`
- `data_processing\decrypt_extracts.py`
- `data_processing\embed_all_sources.py`
- `data_processing\finalize_and_encrypt_sources.py`
- `data_processing\identify_missing_segments.py`
- `data_processing\populate_extract_segments.py`
- `data_processing\prepare_manual_correction.py`
- `data_processing\regenerate_encrypted_definitions.py`
- `demo\DEMO_RHETORICAL_ANALYSIS.md`
- `demo\demo_epita_showcase.py`
- `demo\demo_unified_authentic_system.ps1`
- `demo\test_epita_demo_validation.py`
- `demo\test_system_simple.ps1`
- `demo\test_unified_system_simple.ps1`
- `demo\validation_point3_demo_epita_dynamique.py`
- `diagnose_backend_startup.ps1`
- `diagnostic\README.md`
- `diagnostic\TEST_MAPPING.md`
- `diagnostic\diagnostic_semantic_kernel.py`
- `diagnostic\test_api.py`
- `diagnostic\test_backend_fixed.ps1`
- `diagnostic\test_compatibility_fixes.py`
- `diagnostic\test_critical_dependencies.py`
- `diagnostic\test_importation_consolidee.py`
- `diagnostic\test_intelligent_modal_correction.py`
- `diagnostic\test_orchestration_corrections_sherlock_watson.py`
- `diagnostic\test_performance_systeme.py`
- `diagnostic\test_robustesse_systeme.py`
- `diagnostic\test_system_stability.py`
- `diagnostic\test_unified_system.py`
- `diagnostic\test_validation_environnement.py`
- `diagnostic\test_web_api_direct.py`
- `diagnostic\verifier_regression_rapide.py`
- `diagnostic_git_corruption.ps1`
- `env\activate_project_env.ps1`
- `env\check_environment.py`
- `env\diagnose_environment.py`
- `env\environment_helpers.py`
- `env\fix_encoding_issues.py`
- `env\manage_environment.py`
- `env\setup_project_env.sh.old`
- `env\update_demo_scripts.py`
- `execution\README.md`
- `execution\README_rhetorical_analysis.md`
- `execution\run_extract_repair.py`
- `execution\run_verify_extracts.py`
- `find_obsolete_test_references.ps1`
- `fix\fix_agents_imports.ps1`
- `fix\fix_authorrole_imports.ps1`
- `fix\fix_exception_imports.ps1`
- `generate_and_apply_corrections.ps1`
- `git_conflict_resolver.ps1`
- `legacy_root\activate_project_env.ps1`
- `legacy_root\run_all_new_component_tests.ps1`
- `legacy_root\run_sherlock_watson_synthetic_validation.ps1`
- `legacy_root\run_tests.ps1`
- `legacy_root\setup_project_env.ps1`
- `maintenance\README.md`
- `maintenance\analyze_documentation_results.py`
- `maintenance\analyze_obsolete_documentation.py`
- `maintenance\analyze_obsolete_documentation_rebuilt.py`
- `maintenance\analyze_oracle_references_detailed.py`
- `maintenance\apply_path_corrections_logged.py`
- `maintenance\auto_fix_documentation.py`
- `maintenance\auto_resolve_git_conflicts.ps1`
- `maintenance\check_imports.py`
- `maintenance\cleanup_obsolete_files.py`
- `maintenance\comprehensive_documentation_fixer_safe.py`
- `maintenance\comprehensive_documentation_recovery.py`
- `maintenance\correct_french_sources_config.py`
- `maintenance\correct_source_paths.py`
- `maintenance\depot_cleanup_migration.ps1`
- `maintenance\depot_cleanup_migration_simple.ps1`
- `maintenance\diagnostic_liens_precis.py`
- `maintenance\final_system_validation.py`
- `maintenance\final_system_validation_corrected.py`
- `maintenance\finalize_refactoring.py`
- `maintenance\fix_project_structure.py`
- `maintenance\git_files_inventory.py`
- `maintenance\git_files_inventory_fast.py`
- `maintenance\git_files_inventory_simple.py`
- `maintenance\integrate_recovered_code.py`
- `maintenance\organize_orphan_files.py`
- `maintenance\organize_orphan_tests.py`
- `maintenance\organize_orphans_execution.py`
- `maintenance\organize_root_files.py`
- `maintenance\orphan_files_processor.py`
- `maintenance\quick_documentation_fixer.py`
- `maintenance\real_orphan_files_processor.py`
- `maintenance\recover_precious_code.py`
- `maintenance\recovered\validate_oracle_coverage.py`
- `maintenance\recovery_assistant.py`
- `maintenance\refactor_oracle_system.py`
- `maintenance\refactor_review_files.py`
- `maintenance\remove_source_from_config.py`
- `maintenance\run_documentation_maintenance.py`
- `maintenance\safe_file_deletion.py`
- `maintenance\test_imports.py`
- `maintenance\test_imports_after_reorg.py`
- `maintenance\test_oracle_enhanced_compatibility.py`
- `maintenance\unified_maintenance.py`
- `maintenance\update_documentation.py`
- `maintenance\update_imports.py`
- `maintenance\update_paths.py`
- `maintenance\update_test_coverage.py`
- `maintenance\validate_migration.ps1`
- `maintenance\validate_oracle_coverage.py`
- `maintenance\verify_content_integrity.py`
- `maintenance\verify_files.py`
- `migrate_to_unified.py`
- `orchestration_validation.py`
- `report_potential_corrections.ps1`
- `reporting\README.md`
- `reporting\README_compare_rhetorical_agents.md`
- `reporting\compare_rhetorical_agents.py`
- `reporting\compare_rhetorical_agents_simple.py`
- `reporting\generate_cluedo_oracle_trace.py`
- `reporting\generate_comprehensive_report.py`
- `reporting\generate_coverage_report.py`
- `reporting\generate_rhetorical_analysis_summaries.py`
- `reporting\initialize_coverage_history.py`
- `reporting\update_coverage_in_report.py`
- `reporting\update_main_report_file.py`
- `reporting\visualize_test_coverage.py`
- `reports\cleanup_migration_duplicates.py`
- `reports\migration_duplicates_analysis.md`
- `reports\migration_duplicates_data.json`
- `run_all_and_test.ps1`
- `setup\README.md`
- `setup\README_INSTALLATION_OUTILS_COMPILATION.md`
- `setup\README_PYTHON312_COMPATIBILITY.md`
- `setup\adapt_code_for_pyjnius.py`
- `setup\check_jpype_import.py`
- `setup\diagnostic_environnement.py`
- `setup\download_test_jars.py`
- `setup\fix_all_dependencies.ps1`
- `setup\fix_all_dependencies.py`
- `setup\fix_dependencies.ps1`
- `setup\fix_dependencies.py`
- `setup\fix_dependencies_for_python312.ps1`
- `setup\fix_environment_auto.py`
- `setup\fix_pydantic_torch_deps.ps1`
- `setup\fix_pythonpath_manual.py`
- `setup\fix_pythonpath_simple.py`
- `setup\init_jpype_compatibility.py`
- `setup\install_build_tools.ps1`
- `setup\install_environment.py.old`
- `setup\install_jpype_for_python312.ps1`
- `setup\install_jpype_for_python313.ps1`
- `setup\install_jpype_with_vcvars.ps1`
- `setup\install_prebuilt_dependencies.ps1`
- `setup\install_prebuilt_wheels.ps1`
- `setup\run_mock_tests.py`
- `setup\run_tests_with_mock.py`
- `setup\run_with_vcvars.ps1`
- `setup\setup_jpype_mock.ps1`
- `setup\setup_test_env.ps1`
- `setup\setup_test_env.py`
- `setup\test_all_dependencies.ps1`
- `setup\test_all_dependencies.py`
- `setup\test_dependencies.ps1`
- `setup\test_dependencies.py`
- `setup\validate_environment.py`
- `setup_core\__init__.py`
- `setup_core\env_utils.py`
- `setup_core\main_setup.py`
- `setup_core\manage_conda_env.py`
- `setup_core\manage_portable_tools.py`
- `setup_core\manage_project_files.py`
- `setup_core\run_pip_commands.py`
- `sherlock_watson\orchestrate_dynamic_cases.py`
- `sherlock_watson\run_authentic_sherlock_watson_investigation.py`
- `sherlock_watson\run_authentic_sherlock_watson_no_java.py`
- `sherlock_watson\run_cluedo_oracle_enhanced.py`
- `sherlock_watson\run_einstein_oracle_demo.py`
- `sherlock_watson\run_real_sherlock_watson_moriarty.py`
- `sherlock_watson\run_sherlock_watson_investigation_complete.py`
- `sherlock_watson\run_sherlock_watson_moriarty_no_tweety.py`
- `sherlock_watson\run_sherlock_watson_moriarty_robust.py`
- `sherlock_watson\test_oracle_behavior_demo.py`
- `sherlock_watson\test_oracle_behavior_simple.py`
- `sherlock_watson\validation_point1_simple.py`
- `start_full_app.ps1`
- `test_playwright_headless.ps1`
- `testing\README.md`
- `testing\debug_test_crypto_cycle.py`
- `testing\get_test_metrics.py`
- `testing\run_all_embed_tests.py`
- `testing\run_embed_tests.py`
- `testing\run_tests_alternative.py`
- `testing\simple_test_runner.py`
- `testing\test_runner_simple.py`
- `testing\validate_embed_tests.py`
- `unified_utilities.py`
- `update_references.ps1`
- `utils\RAPPORT_COMPLETION_EXTRACTION_EXTRAITS.md`
- `utils\README.md`
- `utils\README_decrypt_system.md`
- `utils\analyze_directory_usage.py`
- `utils\check_encoding.py`
- `utils\check_modules.py`
- `utils\check_syntax.py`
- `utils\cleanup_redundant_files.py`
- `utils\cleanup_sensitive_traces.py`
- `utils\create_test_encrypted_extracts.py`
- `utils\fix_docstrings.py`
- `utils\fix_encoding.py`
- `utils\fix_indentation.py`
- `utils\inspect_specific_sources.py`
- `utils\script_commits.ps1`
- `utils\test_imports_utils.py`
- `utils\test_imports_utils_impl.py`
- `validation\README.md`
- `validation\compare_markdown.ps1`
- `validation\diagnostic_dependencies.py`
- `validation\diagnostic_imports_real_llm_orchestrator.py`
- `validation\legacy\VALIDATION_MIGRATION_IMMEDIATE.py`
- `validation\legacy\audit_validation_exhaustive.py`
- `validation\legacy\generate_conversation_analysis_report.py`
- `validation\legacy\generate_final_validation_report.py`
- `validation\legacy\generate_orchestration_conformity_report.py`
- `validation\legacy\generate_validation_report.py`
- `validation\legacy\validation_migration_phase_2b.py`
- `validation\legacy\validation_migration_simple.py`
- `validation\mock_elimination.py`
- `validation\test_ascii_validation.py`
- `validation\test_epita_custom_data_processing.py`
- `validation\test_simple_custom_data.py`
- `validation\unified_validation.py`
- `validation\validate_consolidated_system.py`
- `validation\validate_migration.py`
- `validation\validate_section_anchors.ps1`
- `validation\validate_system_security.py`
- `validation\validate_toc_anchors.ps1`
- `validation\verify_project_structure.ps1`
- `validation_finale_success_demonstration.py`
- `webapp\__init__.py`
- `webapp\backend_info.json`
- `webapp\backend_manager.py`
- `webapp\cleanup_redundant_scripts.py`
- `webapp\config\webapp_config.yml`
- `webapp\debug_direct_launch.py`
- `webapp\frontend_manager.py`
- `webapp\logs\traces\test_report.json`
- `webapp\logs\webapp_integration_trace.md`
- `webapp\minimal_backend_for_tests.py`
- `webapp\playwright_runner.py`
- `webapp\process_cleaner.py`
- `webapp\test_backend_simple.py`
- `webapp\test_orchestrator.py`
- `webapp\unified_web_orchestrator.py`
