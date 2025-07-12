$files = @(
    "argumentation_analysis/agents/agent_factory.py",
    "argumentation_analysis/agents/core/extract/extract_agent.py",
    "argumentation_analysis/agents/core/informal/informal_agent.py",
    "argumentation_analysis/agents/core/logic/propositional_logic_agent.py",
    "argumentation_analysis/agents/core/logic/watson_logic_assistant.py",
    "argumentation_analysis/agents/core/pm/pm_agent.py",
    "argumentation_analysis/agents/core/pm/sherlock_enquete_agent.py",
    "argumentation_analysis/analytics/text_analyzer.py",
    "argumentation_analysis/demos/run_rhetorical_analysis_demo.py",
    "argumentation_analysis/orchestration/analysis_runner.py",
    "argumentation_analysis/orchestration/cluedo_extended_orchestrator.py",
    "config/ports.json",
    "config/webapp_config.yml",
    "docs/rhetorical_analysis_architecture.md",
    "examples/scripts_demonstration/generate_complex_synthetic_data.py",
    "scripts/apps/webapp/backend_manager.py",
    "scripts/orchestration/pipelines/run_rhetorical_analysis_pipeline.py",
    "services/web_api/interface-web-argumentative/package.json"
)

foreach ($file in $files) {
    Write-Output "=================================================="
    Write-Output "### ANALYZING FILE: $file"
    Write-Output "=================================================="
    Write-Output "--- GIT LOG ---"
    git log --follow --oneline -n 5 -- $file
    Write-Output ""
    Write-Output "--- GIT DIFF ---"
    git diff HEAD -- $file
    Write-Output ""
}