param(
    [Parameter(Mandatory=$true, ValueFromRemainingArguments=$true)]
    [string[]]$CommandToRun
)

# Activer l'environnement Conda
conda activate projet-is

# Exécuter la commande fournie
if ($CommandToRun) {
    $command = $CommandToRun -join " "
    Write-Host "Executing in 'projet-is': $command"
    Invoke-Expression $command
}