# Script pour supprimer les anciens répertoires d'agents qui ont été migrés vers la nouvelle structure

$oldDirs = @(
    "argumentiation_analysis/agents/extract",
    "argumentiation_analysis/agents/informal",
    "argumentiation_analysis/agents/pl",
    "argumentiation_analysis/agents/analysis_scripts",
    "argumentiation_analysis/agents/documentation",
    "argumentiation_analysis/agents/execution_traces",
    "argumentiation_analysis/agents/run_scripts",
    "argumentiation_analysis/agents/traces_informal_agent",
    "argumentiation_analysis/agents/traces_orchestration_complete"
)

foreach ($dir in $oldDirs) {
    if (Test-Path $dir) {
        Write-Host "Suppression du répertoire: $dir"
        Remove-Item -Path $dir -Recurse -Force
    } else {
        Write-Host "Le répertoire $dir n'existe pas ou a déjà été supprimé."
    }
}

Write-Host "Nettoyage terminé."